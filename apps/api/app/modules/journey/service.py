import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.contracts.events import JourneyEvent
from app.modules.journey.models import (
    CustomerModel,
    FinancialProductModel,
    IdempotencyRecordModel,
    JourneyEventModel,
    JourneyModel,
)
from app.modules.journey.schemas import (
    CreateJourneyRequest,
    EventWriteResult,
    JourneyEventRead,
    JourneyRead,
)
from app.modules.journey.state import project_journey


class JourneyNotFoundError(Exception):
    pass


class JourneyConflictError(Exception):
    pass


@dataclass(frozen=True)
class ProductDefinition:
    name: str
    requirements: dict[str, list[str]]


PRODUCTS = {
    "SOLE_PROPRIETOR_LOAN": ProductDefinition(
        name="개인사업자 신용대출",
        requirements={
            "checks": ["identity_verification", "limit_check", "income_verification"],
            "documents": ["income_verification_result"],
        },
    )
}


def request_hash(event: JourneyEvent) -> str:
    payload = json.dumps(
        event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def event_contract(model: JourneyEventModel) -> JourneyEvent:
    return JourneyEvent(
        schema_version=model.schema_version,
        event_id=model.id,
        customer_id=model.customer_id,
        journey_id=model.journey_id,
        session_id=model.session_id,
        channel=model.channel,
        event_type=model.event_type,
        product_type=model.product_type,
        journey_step=model.journey_step,
        status=model.status,
        error_code=model.error_code,
        retry_count=model.retry_count,
        occurred_at=model.occurred_at,
        duration_ms=model.duration_ms,
        attributes=model.attributes,
    )


def event_read(model: JourneyEventModel) -> JourneyEventRead:
    return JourneyEventRead(**event_contract(model).model_dump(), created_at=model.created_at)


def journey_read(model: JourneyModel) -> JourneyRead:
    return JourneyRead(
        id=model.id,
        customer_id=model.customer_id,
        product_type=model.product.product_code,
        status=model.status,
        current_step=model.current_step,
        started_at=model.started_at,
        updated_at=model.updated_at,
        events=[event_read(event) for event in model.events],
    )


def load_journey(session: Session, journey_id: UUID) -> JourneyModel:
    statement = (
        select(JourneyModel)
        .where(JourneyModel.id == journey_id)
        .options(selectinload(JourneyModel.product), selectinload(JourneyModel.events))
    )
    journey = session.scalar(statement)
    if journey is None:
        raise JourneyNotFoundError(str(journey_id))
    return journey


def get_or_create_product(session: Session, product_code: str) -> FinancialProductModel:
    product = session.scalar(
        select(FinancialProductModel).where(FinancialProductModel.product_code == product_code)
    )
    if product is not None:
        return product
    definition = PRODUCTS[product_code]
    product = FinancialProductModel(
        product_code=product_code,
        name=definition.name,
        requirements=definition.requirements,
    )
    session.add(product)
    session.flush()
    return product


def create_journey(session: Session, request: CreateJourneyRequest) -> JourneyRead:
    customer = session.get(CustomerModel, request.customer_id) if request.customer_id else None
    if customer is None:
        customer = CustomerModel(id=request.customer_id, segment=request.customer_segment)
        session.add(customer)
        session.flush()
    elif request.customer_segment and customer.segment != request.customer_segment:
        raise JourneyConflictError("customer_id already exists with a different segment")

    product = get_or_create_product(session, request.product_type.value)
    journey = JourneyModel(customer_id=customer.id, product_id=product.id)
    session.add(journey)
    session.commit()
    return journey_read(load_journey(session, journey.id))


def get_journey(session: Session, journey_id: UUID) -> JourneyRead:
    return journey_read(load_journey(session, journey_id))


def append_event(
    session: Session,
    journey_id: UUID,
    event: JourneyEvent,
    idempotency_key: str | None,
) -> EventWriteResult:
    journey = load_journey(session, journey_id)
    digest = request_hash(event)

    if event.journey_id != journey.id:
        raise JourneyConflictError("body journey_id does not match path")
    if event.customer_id != journey.customer_id:
        raise JourneyConflictError("event customer_id does not match journey")
    if event.product_type.value != journey.product.product_code:
        raise JourneyConflictError("event product_type does not match journey")

    if idempotency_key:
        record = session.scalar(
            select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.journey_id == journey_id,
                IdempotencyRecordModel.idempotency_key == idempotency_key,
            )
        )
        if record is not None:
            if record.request_hash != digest:
                raise JourneyConflictError("idempotency key was reused with a different request")
            stored = session.get(JourneyEventModel, record.event_id)
            if stored is None:
                raise JourneyConflictError("idempotency record references a missing event")
            return EventWriteResult(
                event=event_read(stored),
                journey_status=journey.status,
                current_step=journey.current_step,
                idempotent_replay=True,
            )

    stored = session.get(JourneyEventModel, event.event_id)
    if stored is not None:
        if stored.request_hash != digest:
            raise JourneyConflictError("event_id was reused with a different payload")
        return EventWriteResult(
            event=event_read(stored),
            journey_status=journey.status,
            current_step=journey.current_step,
            idempotent_replay=True,
        )

    if journey.events and event.occurred_at < journey.events[-1].occurred_at:
        raise JourneyConflictError("event occurred_at cannot precede the latest journey event")

    stored = JourneyEventModel(
        id=event.event_id,
        schema_version=event.schema_version,
        customer_id=event.customer_id,
        journey_id=event.journey_id,
        session_id=event.session_id,
        channel=event.channel.value,
        event_type=event.event_type.value,
        product_type=event.product_type.value,
        journey_step=event.journey_step.value,
        status=event.status.value,
        error_code=event.error_code,
        retry_count=event.retry_count,
        occurred_at=event.occurred_at,
        duration_ms=event.duration_ms,
        attributes=event.attributes,
        request_hash=digest,
    )
    session.add(stored)
    session.flush()
    all_events = [event_contract(model) for model in journey.events] + [event]
    projection = project_journey(all_events)
    journey.status = projection.status.value
    journey.current_step = projection.current_step.value
    if idempotency_key:
        session.add(
            IdempotencyRecordModel(
                journey_id=journey.id,
                idempotency_key=idempotency_key,
                request_hash=digest,
                event_id=stored.id,
            )
        )
    session.commit()
    session.refresh(stored)
    return EventWriteResult(
        event=event_read(stored),
        journey_status=projection.status,
        current_step=projection.current_step,
        idempotent_replay=False,
    )

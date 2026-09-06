from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.journey.models import (
    ConsentModel,
    ConsultationModel,
    ContextPassModel,
)
from app.modules.journey.schemas import (
    CompleteConsultationRequest,
    ConsentRead,
    ConsultationRead,
    ContextPassRead,
    CreateConsentRequest,
)
from app.modules.journey.service import JourneyConflictError, JourneyNotFoundError, load_journey


def create_consent(
    session: Session, journey_id: UUID, request: CreateConsentRequest
) -> ConsentRead:
    journey = load_journey(session, journey_id)
    now = datetime.now(UTC)
    consent = ConsentModel(
        journey_id=journey.id,
        customer_id=journey.customer_id,
        scope=request.scope,
        expires_at=now + timedelta(minutes=request.ttl_minutes),
    )
    session.add(consent)
    session.commit()
    session.refresh(consent)
    return ConsentRead.model_validate(consent, from_attributes=True)


def revoke_consent(session: Session, consent_id: UUID) -> ConsentRead:
    consent = session.get(ConsentModel, consent_id)
    if consent is None:
        raise JourneyNotFoundError(str(consent_id))
    consent.status = "REVOKED"
    consent.revoked_at = datetime.now(UTC)
    session.commit()
    session.refresh(consent)
    return ConsentRead.model_validate(consent, from_attributes=True)


def create_context_pass(session: Session, journey_id: UUID, consent_id: UUID) -> ContextPassRead:
    journey = load_journey(session, journey_id)
    consent = session.get(ConsentModel, consent_id)
    now = datetime.now(UTC)
    if consent is None or consent.journey_id != journey.id:
        raise JourneyConflictError("consent does not belong to journey")
    if consent.status != "ACTIVE" or consent.expires_at <= now:
        raise JourneyConflictError("consent is not active")
    events = journey.events
    failures = [event for event in events if event.status == "FAILED"]
    payload = {
        "journey_id": str(journey.id),
        "current_product": journey.product.product_code,
        "current_step": journey.current_step,
        "completed_steps": list(
            dict.fromkeys(
                event.journey_step
                for event in events
                if event.status in {"SUCCEEDED", "COMPLETED"}
            )
        ),
        "failure_step": failures[-1].journey_step if failures else None,
        "error_codes": list(
            dict.fromkeys(event.error_code for event in failures if event.error_code)
        ),
        "retry_count": max((event.retry_count for event in events), default=0),
        "customer_intent": "SOLE_PROPRIETOR_LOAN_APPLICATION",
    }
    context_pass = ContextPassModel(
        journey_id=journey.id,
        consent_id=consent.id,
        payload=payload,
        expires_at=consent.expires_at,
    )
    session.add(context_pass)
    session.commit()
    session.refresh(context_pass)
    return ContextPassRead.model_validate(context_pass, from_attributes=True)


def get_context_pass(session: Session, pass_id: UUID) -> ContextPassRead:
    context_pass = session.get(ContextPassModel, pass_id)
    if context_pass is None:
        raise JourneyNotFoundError(str(pass_id))
    if context_pass.expires_at <= datetime.now(UTC):
        raise JourneyConflictError("context pass has expired")
    return ContextPassRead.model_validate(context_pass, from_attributes=True)


def create_consultation(session: Session, pass_id: UUID) -> ConsultationRead:
    context_pass = session.get(ContextPassModel, pass_id)
    if context_pass is None:
        raise JourneyNotFoundError(str(pass_id))
    get_context_pass(session, pass_id)
    consultation = ConsultationModel(journey_id=context_pass.journey_id, context_pass_id=pass_id)
    session.add(consultation)
    session.commit()
    session.refresh(consultation)
    return ConsultationRead.model_validate(consultation, from_attributes=True)


def complete_consultation(
    session: Session, consultation_id: UUID, request: CompleteConsultationRequest
) -> ConsultationRead:
    consultation = session.get(ConsultationModel, consultation_id)
    if consultation is None:
        raise JourneyNotFoundError(str(consultation_id))
    if consultation.status == "COMPLETED":
        raise JourneyConflictError("consultation is already completed")
    consultation.status = "COMPLETED"
    consultation.outcome = request.outcome
    consultation.next_step = request.next_step
    consultation.notes = request.notes
    consultation.completed_at = datetime.now(UTC)
    session.commit()
    session.refresh(consultation)
    return ConsultationRead.model_validate(consultation, from_attributes=True)

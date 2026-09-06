from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.events import JourneyEvent
from app.infrastructure.database import get_session
from app.modules.journey.handoff import (
    complete_consultation,
    create_consent,
    create_consultation,
    create_context_pass,
    get_context_pass,
    revoke_consent,
)
from app.modules.journey.schemas import (
    CompleteConsultationRequest,
    ConsentRead,
    ConsultationRead,
    ContextPassRead,
    CreateConsentRequest,
    CreateJourneyRequest,
    EventWriteResult,
    JourneyRead,
)
from app.modules.journey.service import (
    JourneyConflictError,
    JourneyNotFoundError,
    append_event,
    create_journey,
    get_journey,
)

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_session)]


def not_found(error: JourneyNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="journey not found")


def conflict(error: JourneyConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("", response_model=JourneyRead, status_code=status.HTTP_201_CREATED)
def post_journey(request: CreateJourneyRequest, session: DatabaseSession) -> JourneyRead:
    try:
        return create_journey(session, request)
    except JourneyConflictError as error:
        raise conflict(error) from error


@router.get("/{journey_id}", response_model=JourneyRead)
def read_journey(journey_id: UUID, session: DatabaseSession) -> JourneyRead:
    try:
        return get_journey(session, journey_id)
    except JourneyNotFoundError as error:
        raise not_found(error) from error


@router.post("/{journey_id}/events", response_model=EventWriteResult)
def post_journey_event(
    journey_id: UUID,
    event: JourneyEvent,
    session: DatabaseSession,
    idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
) -> EventWriteResult:
    try:
        return append_event(session, journey_id, event, idempotency_key)
    except JourneyNotFoundError as error:
        raise not_found(error) from error
    except JourneyConflictError as error:
        raise conflict(error) from error


@router.post("/{journey_id}/consents", response_model=ConsentRead, status_code=201)
def post_consent(
    journey_id: UUID, request: CreateConsentRequest, session: DatabaseSession
) -> ConsentRead:
    try:
        return create_consent(session, journey_id, request)
    except JourneyNotFoundError as error:
        raise not_found(error) from error


@router.post("/{journey_id}/context-pass", response_model=ContextPassRead, status_code=201)
def post_context_pass(
    journey_id: UUID, consent_id: UUID, session: DatabaseSession
) -> ContextPassRead:
    try:
        return create_context_pass(session, journey_id, consent_id)
    except JourneyNotFoundError as error:
        raise not_found(error) from error
    except JourneyConflictError as error:
        raise conflict(error) from error


@router.get("/context-pass/{pass_id}", response_model=ContextPassRead)
def read_context_pass(pass_id: UUID, session: DatabaseSession) -> ContextPassRead:
    try:
        return get_context_pass(session, pass_id)
    except JourneyNotFoundError as error:
        raise not_found(error) from error
    except JourneyConflictError as error:
        raise conflict(error) from error


@router.post("/consents/{consent_id}/revoke", response_model=ConsentRead)
def post_revoke_consent(consent_id: UUID, session: DatabaseSession) -> ConsentRead:
    try:
        return revoke_consent(session, consent_id)
    except JourneyNotFoundError as error:
        raise not_found(error) from error


@router.post(
    "/context-pass/{pass_id}/consultations", response_model=ConsultationRead, status_code=201
)
def post_consultation(pass_id: UUID, session: DatabaseSession) -> ConsultationRead:
    try:
        return create_consultation(session, pass_id)
    except JourneyNotFoundError as error:
        raise not_found(error) from error
    except JourneyConflictError as error:
        raise conflict(error) from error


@router.post("/consultations/{consultation_id}/complete", response_model=ConsultationRead)
def post_complete_consultation(
    consultation_id: UUID, request: CompleteConsultationRequest, session: DatabaseSession
) -> ConsultationRead:
    try:
        return complete_consultation(session, consultation_id, request)
    except JourneyNotFoundError as error:
        raise not_found(error) from error
    except JourneyConflictError as error:
        raise conflict(error) from error

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.events import JourneyEvent
from app.infrastructure.database import get_session
from app.modules.journey.schemas import CreateJourneyRequest, EventWriteResult, JourneyRead
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

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.ai import ContextInterpretation, RecommendedActionOutput
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
from app.modules.journey.interpretation import interpret_journey
from app.modules.journey.recommendations import recommend_actions
from app.modules.journey.schemas import (
    CompleteConsultationRequest,
    ConsentRead,
    ConsultationRead,
    ContextPassRead,
    CreateConsentRequest,
    CreateJourneyRequest,
    EventWriteResult,
    JourneyRead,
    JourneyChatRequest,
    JourneyChatResponse,
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


@router.post("/{journey_id}/analyze", response_model=ContextInterpretation)
def analyze_journey(journey_id: UUID, session: DatabaseSession) -> ContextInterpretation:
    try:
        return interpret_journey(session, journey_id)
    except JourneyNotFoundError as error:
        raise not_found(error) from error


@router.post("/{journey_id}/chat", response_model=JourneyChatResponse)
def chat_about_journey(
    journey_id: UUID, request: JourneyChatRequest, session: DatabaseSession
) -> JourneyChatResponse:
    """Answer a customer question using only the current Journey context."""
    try:
        interpretation = interpret_journey(session, journey_id)
    except JourneyNotFoundError as error:
        raise not_found(error) from error

    error_text = ", ".join(interpretation.error_codes) or "없음"
    answer = (
        f"현재 {interpretation.current_step.value} 단계에서 {error_text} 오류가 "
        f"{interpretation.retry_count}회 확인되었습니다. "
        "잠시 후 다시 시도해도 같은 문제가 반복되면, 사업자 소득금액증명원이나 "
        "부가세 과세표준증명원으로 대체 제출할 수 있습니다. "
        "상담원이 지금 진행 상황을 이어받을 수 있도록 가까운 영업점 방문 또는 "
        "콜센터 연결을 권해드립니다."
    )
    return JourneyChatResponse(
        answer=answer,
        current_step=interpretation.current_step,
        error_codes=interpretation.error_codes,
        retry_count=interpretation.retry_count,
        suggested_channels=["CALL_CENTER", "BRANCH"],
        context_used=["CURRENT_STEP", "FAILURE_EVIDENCE", "RETRY_COUNT", "CUSTOMER_INTENT"],
    )


@router.get("/{journey_id}/actions", response_model=list[RecommendedActionOutput])
def get_journey_actions(
    journey_id: UUID, session: DatabaseSession
) -> list[RecommendedActionOutput]:
    try:
        return recommend_actions(session, journey_id)
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

from app.contracts.ai import ContextInterpretation, EvidenceReference
from app.contracts.events import EventStatus
from app.modules.journey.intent import classify_intent
from app.modules.journey.service import event_contract, load_journey


def interpret_journey(session, journey_id) -> ContextInterpretation:
    journey = load_journey(session, journey_id)
    events = [event_contract(event) for event in journey.events]
    failures = [event for event in events if event.status == EventStatus.FAILED]
    completed_steps = list(
        dict.fromkeys(event.journey_step for event in events if event.status != EventStatus.FAILED)
    )
    error_codes = list(dict.fromkeys(event.error_code for event in failures if event.error_code))
    retry_count = max((event.retry_count for event in events), default=0)
    failure_step = failures[-1].journey_step if failures else None
    customer_intent, intent_confidence = classify_intent(journey.current_step, error_codes)
    if failure_step and error_codes:
        summary = (
            f"고객은 개인사업자 신용대출 신청 중 {failure_step.value} 단계에서 "
            f"{', '.join(error_codes)} 오류를 {retry_count}회 경험했습니다. "
            "상담원이 대체 절차와 추가서류를 확인해야 합니다."
        )
    else:
        summary = f"고객은 개인사업자 신용대출의 {journey.current_step} 단계까지 진행했습니다."
    return ContextInterpretation(
        journey_id=journey.id,
        current_step=journey.current_step,
        completed_steps=completed_steps,
        failure_step=failure_step,
        error_codes=error_codes,
        retry_count=retry_count,
        customer_intent=customer_intent,
        intent_confidence=intent_confidence,
        intent_source="RULE",
        summary=summary,
        evidence=[
            EvidenceReference(source_type="JOURNEY_EVENT", source_id=str(event.event_id))
            for event in events[-5:]
        ],
    )

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.journey.models import JourneyEventModel, JourneyModel
from app.modules.journey.schemas import AnalyticsFailure, AnalyticsInsight, AnalyticsSummary


def summarize(session: Session) -> AnalyticsSummary:
    journeys = list(session.scalars(select(JourneyModel)))
    total = len(journeys)
    completed = sum(journey.status == "COMPLETED" for journey in journeys)
    assisted = sum(
        journey.status in {"SUPPORT_REQUESTED", "IN_CONSULTATION", "RESUMED"}
        for journey in journeys
    )
    events = list(session.scalars(select(JourneyEventModel)))
    durations = [event.duration_ms for event in events if event.duration_ms is not None]
    return AnalyticsSummary(
        total_journeys=total,
        completion_rate=round(completed / total * 100, 1) if total else 0,
        failure_rate=round(sum(event.status == "FAILED" for event in events) / len(events) * 100, 1)
        if events
        else 0,
        support_conversion_rate=round(assisted / total * 100, 1) if total else 0,
        average_journey_duration_ms=round(sum(durations) / len(durations)) if durations else 0,
        top_failure_step=next(
            iter(
                Counter(
                    event.journey_step for event in events if event.status == "FAILED"
                ).most_common()
            ),
            (None, 0),
        )[0],
        top_error_code=next(
            iter(Counter(event.error_code for event in events if event.error_code).most_common()),
            (None, 0),
        )[0],
    )


def failures(session: Session) -> list[AnalyticsFailure]:
    events = list(
        session.scalars(select(JourneyEventModel).where(JourneyEventModel.status == "FAILED"))
    )
    by_step = Counter(event.journey_step for event in events)
    by_error = Counter(event.error_code for event in events if event.error_code)
    result = [
        AnalyticsFailure(category="step", key=key, count=count)
        for key, count in by_step.most_common()
    ]
    result.extend(
        AnalyticsFailure(category="error_code", key=key, count=count)
        for key, count in by_error.most_common()
    )
    return result


def insight(session: Session) -> AnalyticsInsight:
    summary = summarize(session)
    failures_by_key = failures(session)
    if summary.top_error_code:
        text = (
            f"현재 가장 많은 실패 오류는 {summary.top_error_code}이며, "
            f"실패 집중 단계는 {summary.top_failure_step or '확인 중'}입니다. "
            f"상담 전환율은 {summary.support_conversion_rate}%입니다."
        )
    else:
        text = "아직 실패 이벤트가 없어 구조적 병목을 분석할 데이터가 부족합니다."
    return AnalyticsInsight(text=text, based_on=failures_by_key[:5])

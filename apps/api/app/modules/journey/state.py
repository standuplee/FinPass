from dataclasses import dataclass

from app.contracts.events import EventStatus, EventType, JourneyEvent, JourneyStep
from app.contracts.journey import JourneyStatus


@dataclass(frozen=True)
class JourneyProjection:
    status: JourneyStatus
    current_step: JourneyStep
    failure_count: int


def project_journey(events: list[JourneyEvent]) -> JourneyProjection:
    """Reference projection for contract fixtures, not the Phase 1 persistence engine."""
    if not events:
        raise ValueError("at least one event is required")

    ordered_events = sorted(events, key=lambda event: event.occurred_at)
    latest = ordered_events[-1]
    failure_count = sum(event.status == EventStatus.FAILED for event in ordered_events)

    if latest.event_type == EventType.JOURNEY_COMPLETED:
        status = JourneyStatus.COMPLETED
    elif latest.event_type == EventType.SUPPORT_REQUESTED:
        status = JourneyStatus.SUPPORT_REQUESTED
    elif latest.event_type == EventType.JOURNEY_RESUMED:
        status = JourneyStatus.RESUMED
    elif failure_count >= 3:
        status = JourneyStatus.ASSISTANCE_RECOMMENDED
    else:
        status = JourneyStatus.IN_PROGRESS

    return JourneyProjection(
        status=status,
        current_step=latest.journey_step,
        failure_count=failure_count,
    )

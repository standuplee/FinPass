from fastapi import APIRouter

from app.contracts.events import EventType, JourneyStep

router = APIRouter()


@router.get("/event-catalog")
def event_catalog() -> dict[str, list[str]]:
    return {
        "event_types": [value.value for value in EventType],
        "journey_steps": [value.value for value in JourneyStep],
    }

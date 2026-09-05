from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.events import JourneyEvent, JourneyStep


class JourneyStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    ASSISTANCE_RECOMMENDED = "ASSISTANCE_RECOMMENDED"
    SUPPORT_REQUESTED = "SUPPORT_REQUESTED"
    IN_CONSULTATION = "IN_CONSULTATION"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    RESUMED = "RESUMED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class JourneyFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_version: str = "1.0"
    name: str
    expected_status: JourneyStatus
    expected_current_step: JourneyStep
    expected_failure_count: int = Field(ge=0)
    events: list[JourneyEvent] = Field(min_length=1)

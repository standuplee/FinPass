from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.events import JourneyStep


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: Literal["JOURNEY_EVENT", "MANUAL", "PRODUCT", "CONSULTATION_CASE"]
    source_id: str
    source_version: str | None = None


class ContextInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    journey_id: UUID
    current_step: JourneyStep
    completed_steps: list[JourneyStep]
    failure_step: JourneyStep | None = None
    error_codes: list[str]
    retry_count: Annotated[int, Field(ge=0)]
    customer_intent: str
    intent_confidence: Annotated[float, Field(ge=0, le=1)] = 0.0
    intent_source: Literal["RULE", "BANKING77", "LLM"] = "RULE"
    summary: str
    evidence: list[EvidenceReference] = Field(min_length=1)


class RecommendedActionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_code: str
    title: str
    description: str
    rationale: str
    conditions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(min_length=1)

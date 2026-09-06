from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.events import JourneyEvent, JourneyStep, ProductType
from app.contracts.journey import JourneyStatus


class CreateJourneyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: UUID | None = None
    customer_segment: dict[str, Any] = Field(default_factory=dict)
    product_type: ProductType = ProductType.SOLE_PROPRIETOR_LOAN


class JourneyEventRead(JourneyEvent):
    created_at: datetime


class JourneyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    product_type: ProductType
    status: JourneyStatus
    current_step: JourneyStep
    started_at: datetime
    updated_at: datetime
    events: list[JourneyEventRead] = Field(default_factory=list)


class EventWriteResult(BaseModel):
    event: JourneyEventRead
    journey_status: JourneyStatus
    current_step: JourneyStep
    idempotent_replay: bool


class CreateConsentRequest(BaseModel):
    scope: list[str] = Field(default_factory=lambda: ["JOURNEY_CONTEXT"])
    ttl_minutes: int = Field(default=30, ge=1, le=1440)


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    journey_id: UUID
    customer_id: UUID
    scope: list[str]
    status: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None


class ContextPassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    journey_id: UUID
    consent_id: UUID
    payload: dict[str, Any]
    created_at: datetime
    expires_at: datetime


class ConsultationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    journey_id: UUID
    context_pass_id: UUID | None
    status: str
    outcome: str | None
    next_step: str | None
    notes: str | None
    created_at: datetime
    completed_at: datetime | None


class CompleteConsultationRequest(BaseModel):
    outcome: str = Field(min_length=1, max_length=200)
    next_step: str = Field(min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=4000)

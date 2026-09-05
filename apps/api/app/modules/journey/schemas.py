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

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Channel(StrEnum):
    CUSTOMER_APP = "CUSTOMER_APP"
    CHATBOT = "CHATBOT"
    CALL_CENTER = "CALL_CENTER"
    BRANCH = "BRANCH"


class ProductType(StrEnum):
    SOLE_PROPRIETOR_LOAN = "SOLE_PROPRIETOR_LOAN"


class JourneyStep(StrEnum):
    PRODUCT_SELECTION = "PRODUCT_SELECTION"
    BUSINESS_INFORMATION = "BUSINESS_INFORMATION"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    LIMIT_CHECK = "LIMIT_CHECK"
    INCOME_VERIFICATION = "INCOME_VERIFICATION"
    DOCUMENT_SUBMISSION = "DOCUMENT_SUBMISSION"
    APPLICATION_COMPLETION = "APPLICATION_COMPLETION"
    SUPPORT = "SUPPORT"


class EventStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REQUESTED = "REQUESTED"
    COMPLETED = "COMPLETED"


class EventType(StrEnum):
    JOURNEY_STARTED = "JOURNEY_STARTED"
    PRODUCT_VIEWED = "PRODUCT_VIEWED"
    BUSINESS_INFORMATION_COMPLETED = "BUSINESS_INFORMATION_COMPLETED"
    IDENTITY_VERIFICATION_STARTED = "IDENTITY_VERIFICATION_STARTED"
    IDENTITY_VERIFICATION_COMPLETED = "IDENTITY_VERIFICATION_COMPLETED"
    LIMIT_CHECK_STARTED = "LIMIT_CHECK_STARTED"
    LIMIT_CHECK_COMPLETED = "LIMIT_CHECK_COMPLETED"
    INCOME_VERIFICATION_STARTED = "INCOME_VERIFICATION_STARTED"
    INCOME_VERIFICATION_COMPLETED = "INCOME_VERIFICATION_COMPLETED"
    INCOME_VERIFICATION_FAILED = "INCOME_VERIFICATION_FAILED"
    DOCUMENT_UPLOAD_STARTED = "DOCUMENT_UPLOAD_STARTED"
    DOCUMENT_UPLOAD_COMPLETED = "DOCUMENT_UPLOAD_COMPLETED"
    DOCUMENT_UPLOAD_FAILED = "DOCUMENT_UPLOAD_FAILED"
    SUPPORT_REQUESTED = "SUPPORT_REQUESTED"
    CONTEXT_SHARING_CONSENTED = "CONTEXT_SHARING_CONSENTED"
    CALL_STARTED = "CALL_STARTED"
    CALL_COMPLETED = "CALL_COMPLETED"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    JOURNEY_RESUMED = "JOURNEY_RESUMED"
    JOURNEY_COMPLETED = "JOURNEY_COMPLETED"


class JourneyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    event_id: UUID
    customer_id: UUID
    journey_id: UUID
    session_id: UUID
    channel: Channel
    event_type: EventType
    product_type: ProductType
    journey_step: JourneyStep
    status: EventStatus
    error_code: str | None = None
    retry_count: Annotated[int, Field(ge=0)] = 0
    occurred_at: datetime
    duration_ms: Annotated[int | None, Field(ge=0)] = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_failure_fields(self) -> "JourneyEvent":
        if self.status == EventStatus.FAILED and not self.error_code:
            raise ValueError("failed events require error_code")
        if self.status != EventStatus.FAILED and self.error_code:
            raise ValueError("error_code is allowed only for failed events")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone offset")
        return self

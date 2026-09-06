from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    segment: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    journeys: Mapped[list["JourneyModel"]] = relationship(back_populates="customer")


class FinancialProductModel(Base):
    __tablename__ = "financial_products"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    requirements: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    journeys: Mapped[list["JourneyModel"]] = relationship(back_populates="product")


class JourneyModel(Base):
    __tablename__ = "journeys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("financial_products.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="IN_PROGRESS")
    current_step: Mapped[str] = mapped_column(String(40), default="PRODUCT_SELECTION")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    customer: Mapped[CustomerModel] = relationship(back_populates="journeys")
    product: Mapped[FinancialProductModel] = relationship(back_populates="journeys")
    events: Mapped[list["JourneyEventModel"]] = relationship(
        back_populates="journey", order_by="JourneyEventModel.occurred_at"
    )


class JourneyEventModel(Base):
    __tablename__ = "journey_events"
    __table_args__ = (
        Index("ix_journey_events_journey_occurred", "journey_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0")
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    journey_id: Mapped[UUID] = mapped_column(ForeignKey("journeys.id"), index=True)
    session_id: Mapped[UUID] = mapped_column(index=True)
    channel: Mapped[str] = mapped_column(String(30))
    event_type: Mapped[str] = mapped_column(String(60))
    product_type: Mapped[str] = mapped_column(String(64))
    journey_step: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(40))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    journey: Mapped[JourneyModel] = relationship(back_populates="events")


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("journey_id", "idempotency_key", name="uq_idempotency_journey_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    journey_id: Mapped[UUID] = mapped_column(ForeignKey("journeys.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    event_id: Mapped[UUID] = mapped_column(ForeignKey("journey_events.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConsentModel(Base):
    __tablename__ = "consents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    journey_id: Mapped[UUID] = mapped_column(ForeignKey("journeys.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    scope: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContextPassModel(Base):
    __tablename__ = "context_passes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    journey_id: Mapped[UUID] = mapped_column(ForeignKey("journeys.id"), index=True)
    consent_id: Mapped[UUID] = mapped_column(ForeignKey("consents.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConsultationModel(Base):
    __tablename__ = "consultations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    journey_id: Mapped[UUID] = mapped_column(ForeignKey("journeys.id"), index=True)
    context_pass_id: Mapped[UUID | None] = mapped_column(ForeignKey("context_passes.id"))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    outcome: Mapped[str | None] = mapped_column(String(200))
    next_step: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RagDocumentModel(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    text: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

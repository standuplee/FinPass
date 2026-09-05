"""Create journey core tables.

Revision ID: 20260906_0001
Revises:
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("segment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "financial_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_code"),
    )
    op.create_table(
        "journeys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("current_step", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["financial_products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_journeys_customer_id"), "journeys", ["customer_id"])
    op.create_index(op.f("ix_journeys_product_id"), "journeys", ["product_id"])
    op.create_table(
        "journey_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("journey_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("product_type", sa.String(length=64), nullable=False),
        sa.Column("journey_step", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_journey_events_customer_id"), "journey_events", ["customer_id"])
    op.create_index(op.f("ix_journey_events_journey_id"), "journey_events", ["journey_id"])
    op.create_index(
        "ix_journey_events_journey_occurred",
        "journey_events",
        ["journey_id", "occurred_at"],
    )
    op.create_index(op.f("ix_journey_events_session_id"), "journey_events", ["session_id"])
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journey_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["journey_events.id"]),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("journey_id", "idempotency_key", name="uq_idempotency_journey_key"),
    )
    op.create_index(
        op.f("ix_idempotency_records_journey_id"), "idempotency_records", ["journey_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_idempotency_records_journey_id"), table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index(op.f("ix_journey_events_session_id"), table_name="journey_events")
    op.drop_index("ix_journey_events_journey_occurred", table_name="journey_events")
    op.drop_index(op.f("ix_journey_events_journey_id"), table_name="journey_events")
    op.drop_index(op.f("ix_journey_events_customer_id"), table_name="journey_events")
    op.drop_table("journey_events")
    op.drop_index(op.f("ix_journeys_product_id"), table_name="journeys")
    op.drop_index(op.f("ix_journeys_customer_id"), table_name="journeys")
    op.drop_table("journeys")
    op.drop_table("financial_products")
    op.drop_table("customers")

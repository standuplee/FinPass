"""Add consent, context pass, and consultation tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0002"
down_revision: str | None = "20260906_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journey_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consents_journey_id", "consents", ["journey_id"])
    op.create_index("ix_consents_customer_id", "consents", ["customer_id"])
    op.create_table(
        "context_passes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journey_id", sa.Uuid(), nullable=False),
        sa.Column("consent_id", sa.Uuid(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["consent_id"], ["consents.id"]),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_context_passes_journey_id", "context_passes", ["journey_id"])
    op.create_table(
        "consultations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journey_id", sa.Uuid(), nullable=False),
        sa.Column("context_pass_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.String(length=200), nullable=True),
        sa.Column("next_step", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["context_pass_id"], ["context_passes.id"]),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consultations_journey_id", "consultations", ["journey_id"])


def downgrade() -> None:
    op.drop_index("ix_consultations_journey_id", table_name="consultations")
    op.drop_table("consultations")
    op.drop_index("ix_context_passes_journey_id", table_name="context_passes")
    op.drop_table("context_passes")
    op.drop_index("ix_consents_customer_id", table_name="consents")
    op.drop_index("ix_consents_journey_id", table_name="consents")
    op.drop_table("consents")

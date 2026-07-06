"""Alembic migration: LLM usage monthly budget settings."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "015_llm_usage_budget"
down_revision = "014_llm_usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_budget",
        sa.Column("workspace_id", sa.Text(), primary_key=True),
        sa.Column("monthly_budget_usd", sa.Numeric(), nullable=True),
        sa.Column("alert_threshold_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("llm_usage_budget")

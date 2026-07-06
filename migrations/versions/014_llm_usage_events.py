"""Alembic migration: llm_usage_events table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "014_llm_usage_events"
down_revision = "013_billing_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workspace_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("run_id", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_write_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(), nullable=True),
        sa.Column("cost_status", sa.Text(), nullable=False),
        sa.Column("cost_source", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_llm_usage_recorded_at", "llm_usage_events", ["recorded_at"])
    op.create_index(
        "ix_llm_usage_workspace_recorded",
        "llm_usage_events",
        ["workspace_id", "recorded_at"],
    )
    op.create_index(
        "ix_llm_usage_user_recorded",
        "llm_usage_events",
        ["user_id", "recorded_at"],
    )
    op.create_index(
        "ix_llm_usage_model_recorded",
        "llm_usage_events",
        ["model", "recorded_at"],
    )
    op.create_index(
        "ix_llm_usage_channel_recorded",
        "llm_usage_events",
        ["channel", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_usage_channel_recorded", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_model_recorded", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_user_recorded", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_workspace_recorded", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_recorded_at", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")

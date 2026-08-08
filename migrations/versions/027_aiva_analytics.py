"""Alembic: Aiva analytics daily summaries (K04)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "027_aiva_analytics"
down_revision = "026_aiva_escalation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "aiva_analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False, server_default="1"),
        sa.Column("labels", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_aiva_analytics_events_ws_metric_time",
        "aiva_analytics_events",
        ["workspace_id", "metric_name", "recorded_at"],
    )

    op.create_table(
        "aiva_analytics_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("day", sa.Text(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("labels", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("workspace_id", "day", "metric_name", "labels", name="uq_aiva_analytics_daily"),
    )
    op.create_index("ix_aiva_analytics_daily_ws_day", "aiva_analytics_daily", ["workspace_id", "day"])


def downgrade() -> None:
    op.drop_index("ix_aiva_analytics_daily_ws_day", table_name="aiva_analytics_daily")
    op.drop_table("aiva_analytics_daily")
    op.drop_index("ix_aiva_analytics_events_ws_metric_time", table_name="aiva_analytics_events")
    op.drop_table("aiva_analytics_events")

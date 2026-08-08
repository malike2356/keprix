"""Alembic: keprix_scout_events + keprix_kill_switches (K06)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023_aiva_scout_integration"
down_revision = "022_tenancy_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "keprix_scout_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("prompt_hash", sa.Text(), nullable=True),
        sa.Column("prompt_snippet", sa.Text(), nullable=True),
        sa.Column("tool_name", sa.Text(), nullable=True),
        sa.Column("tool_args_json", sa.Text(), nullable=True),
        sa.Column("tool_result_snippet", sa.Text(), nullable=True),
        sa.Column("response_snippet", sa.Text(), nullable=True),
        sa.Column("scout_verdict", sa.Text(), nullable=True),
        sa.Column("scout_risk_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_keprix_scout_events_workspace_created", "keprix_scout_events", ["workspace_id", "created_at"])
    op.create_index("ix_keprix_scout_events_type", "keprix_scout_events", ["event_type"])

    op.create_table(
        "keprix_kill_switches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("activated_by", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_keprix_kill_switches_workspace_active", "keprix_kill_switches", ["workspace_id", "deactivated_at"])


def downgrade() -> None:
    op.drop_index("ix_keprix_kill_switches_workspace_active", table_name="keprix_kill_switches")
    op.drop_table("keprix_kill_switches")
    op.drop_index("ix_keprix_scout_events_type", table_name="keprix_scout_events")
    op.drop_index("ix_keprix_scout_events_workspace_created", table_name="keprix_scout_events")
    op.drop_table("keprix_scout_events")

"""Alembic: Aiva human VA escalation (K05)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "026_aiva_escalation"
down_revision = "025_worker_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "aiva_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("escalation_type", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("original_input", sa.Text(), nullable=False),
        sa.Column("holding_message", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("assigned_va", sa.Text(), nullable=True),
        sa.Column("va_response", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("notify_log", sa.Text(), nullable=True),
        sa.Column("audit_log", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reassigned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_aiva_escalations_workspace_status", "aiva_escalations", ["workspace_id", "status"])
    op.create_index("ix_aiva_escalations_created", "aiva_escalations", ["created_at"])

    op.create_table(
        "aiva_human_assist_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("urgency", sa.Text(), nullable=False, server_default="normal"),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("aiva_escalations.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_aiva_human_assist_workspace", "aiva_human_assist_requests", ["workspace_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_aiva_human_assist_workspace", table_name="aiva_human_assist_requests")
    op.drop_table("aiva_human_assist_requests")
    op.drop_index("ix_aiva_escalations_created", table_name="aiva_escalations")
    op.drop_index("ix_aiva_escalations_workspace_status", table_name="aiva_escalations")
    op.drop_table("aiva_escalations")

"""Alembic migration: generated tools audit table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "007_generated_tools"
down_revision = "006_slash_command_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_tools",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_that_triggered", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("tool_code", sa.Text(), nullable=False),
        sa.Column("skill_yaml", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("gap_description", sa.Text(), nullable=False),
        sa.Column("static_analysis", sa.JSON(), nullable=False),
        sa.Column("sandbox_result", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("approver_id", sa.Text(), nullable=True),
        sa.Column("approver_channel", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_generated_tools_status_created", "generated_tools", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_generated_tools_status_created", table_name="generated_tools")
    op.drop_table("generated_tools")

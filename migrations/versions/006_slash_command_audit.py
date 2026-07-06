"""Alembic migration: slash command audit log."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "006_slash_command_audit"
down_revision = "005_app_foundation_sdk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slash_command_audit",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=False, server_default="low"),
        sa.Column("confirmation_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("confirmation_token_hash", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_slash_audit_workspace_created", "slash_command_audit", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_slash_audit_workspace_created", table_name="slash_command_audit")
    op.drop_table("slash_command_audit")

"""Alembic migration: system_prompt_versions for prompt mutation (Prompt 152)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "017_prompt_store"
down_revision = "016_mutation_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_prompt_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("prompt_key", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("mutation_id", sa.String(length=36), sa.ForeignKey("mutation_events.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("workspace_id", "prompt_key", "version", name="uq_system_prompt_versions_key_version"),
    )
    op.create_index(
        "ix_system_prompt_versions_workspace_key_active",
        "system_prompt_versions",
        ["workspace_id", "prompt_key", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_system_prompt_versions_workspace_key_active", table_name="system_prompt_versions")
    op.drop_table("system_prompt_versions")

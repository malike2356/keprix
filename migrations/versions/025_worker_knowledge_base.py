"""Alembic: worker knowledge bases (K03)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "025_worker_knowledge_base"
down_revision = "024_outreach_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "worker_knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False, server_default="Default"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("workspace_id", "worker_id", "name", name="uq_worker_kb_workspace_worker_name"),
    )
    op.create_index("ix_worker_knowledge_bases_workspace_worker", "worker_knowledge_bases", ["workspace_id", "worker_id"])

    op.create_table(
        "worker_knowledge_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "knowledge_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("worker_knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("source_file", sa.Text(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_worker_knowledge_entries_kb", "worker_knowledge_entries", ["knowledge_base_id"])
    op.create_index("ix_worker_knowledge_entries_enabled", "worker_knowledge_entries", ["knowledge_base_id", "enabled"])


def downgrade() -> None:
    op.drop_index("ix_worker_knowledge_entries_enabled", table_name="worker_knowledge_entries")
    op.drop_index("ix_worker_knowledge_entries_kb", table_name="worker_knowledge_entries")
    op.drop_table("worker_knowledge_entries")
    op.drop_index("ix_worker_knowledge_bases_workspace_worker", table_name="worker_knowledge_bases")
    op.drop_table("worker_knowledge_bases")

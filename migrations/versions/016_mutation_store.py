"""Alembic migration: mutation_events and mutation_quality_samples."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "016_mutation_store"
down_revision = "015_llm_usage_budget"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mutation_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("tier", sa.Text(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_code", sa.Text(), nullable=True),
        sa.Column("before_value", sa.Text(), nullable=True),
        sa.Column("after_value", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rollback_of", sa.String(length=36), sa.ForeignKey("mutation_events.id"), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_mutation_events_workspace_status", "mutation_events", ["workspace_id", "status"])
    op.create_index("ix_mutation_events_tier_name", "mutation_events", ["tier", "name"])

    op.create_table(
        "mutation_quality_samples",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("mutation_id", sa.String(length=36), sa.ForeignKey("mutation_events.id"), nullable=False),
        sa.Column("sampled_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=True),
        sa.Column("run_id", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
    )
    op.create_index("ix_mutation_quality_mutation_id", "mutation_quality_samples", ["mutation_id"])


def downgrade() -> None:
    op.drop_index("ix_mutation_quality_mutation_id", table_name="mutation_quality_samples")
    op.drop_table("mutation_quality_samples")
    op.drop_index("ix_mutation_events_tier_name", table_name="mutation_events")
    op.drop_index("ix_mutation_events_workspace_status", table_name="mutation_events")
    op.drop_table("mutation_events")

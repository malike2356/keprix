"""Compare latency metrics and user history index."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "018_compare_metrics"
down_revision = "017_prompt_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_comparisons", sa.Column("latency_ms_a", sa.Integer(), nullable=True))
    op.add_column("model_comparisons", sa.Column("latency_ms_b", sa.Integer(), nullable=True))
    op.create_index(
        "ix_model_comparisons_user_created",
        "model_comparisons",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_comparisons_user_created", table_name="model_comparisons")
    op.drop_column("model_comparisons", "latency_ms_b")
    op.drop_column("model_comparisons", "latency_ms_a")

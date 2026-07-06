"""Metrics and request_log tables for observability."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "003_metrics_request_log"
down_revision = "002_research_playbook_compare"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metrics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("metric_type", sa.Text(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Numeric(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_metrics_type_recorded", "metrics", ["metric_type", "recorded_at"])
    op.create_index(
        "ix_metrics_user_type_recorded",
        "metrics",
        ["user_id", "metric_type", "recorded_at"],
    )

    op.create_table(
        "request_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Numeric(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_request_log_recorded", "request_log", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_request_log_recorded", table_name="request_log")
    op.drop_table("request_log")
    op.drop_index("ix_metrics_user_type_recorded", table_name="metrics")
    op.drop_index("ix_metrics_type_recorded", table_name="metrics")
    op.drop_table("metrics")

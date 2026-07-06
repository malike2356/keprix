"""Initial audit_log table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001_audit_log"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.Text(), nullable=True),
        sa.Column("resource_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_audit_log_user_occurred", "audit_log", ["user_id", "occurred_at"])
    op.create_index("ix_audit_log_event_occurred", "audit_log", ["event_type", "occurred_at"])
    op.create_index("ix_audit_log_result_occurred", "audit_log", ["result", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_result_occurred", table_name="audit_log")
    op.drop_index("ix_audit_log_event_occurred", table_name="audit_log")
    op.drop_index("ix_audit_log_user_occurred", table_name="audit_log")
    op.drop_table("audit_log")

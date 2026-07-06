"""Scout governance bridge tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "008_scout_governance"
down_revision = "007_generated_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scout_config",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scout_url", sa.Text(), nullable=True),
        sa.Column("scout_api_key_vault_id", sa.Text(), nullable=True),
        sa.Column("instance_id", sa.Text(), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_ok", sa.Boolean(), nullable=True),
        sa.Column("reporting_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("consecutive_failures", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("vault_user_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_table(
        "scout_event_queue",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_scout_event_queue_sent_id", "scout_event_queue", ["sent", "id"])
    op.create_table(
        "scout_policies",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("policy_type", sa.Text(), nullable=False),
        sa.Column("policy_value", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_table("scout_policies")
    op.drop_index("ix_scout_event_queue_sent_id", table_name="scout_event_queue")
    op.drop_table("scout_event_queue")
    op.drop_table("scout_config")

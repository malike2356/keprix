"""Alembic migration: Channel Shield tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "020_channel_shield"
down_revision = "019_ai_credit_wallet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_shield_protections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("protection_key", sa.Text(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_channel_shield_protections_user_channel",
        "channel_shield_protections",
        ["user_id", "channel"],
    )
    op.create_index(
        "ix_channel_shield_protections_key",
        "channel_shield_protections",
        ["channel", "protection_key"],
    )

    op.create_table(
        "channel_shield_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("protection_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("external_message_id", sa.Text(), nullable=False),
        sa.Column("conversation_id", sa.Text(), nullable=True),
        sa.Column("from_addr", sa.Text(), nullable=True),
        sa.Column("to_addrs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("text_preview", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=True),
        sa.Column("envelope", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("report", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("safe_summary", sa.Text(), nullable=True),
        sa.Column("raw_blob_id", sa.Text(), nullable=True),
        sa.Column("scout_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_channel_shield_messages_user_status",
        "channel_shield_messages",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_channel_shield_messages_channel",
        "channel_shield_messages",
        ["channel", "created_at"],
    )

    op.create_table(
        "channel_shield_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("blob_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_channel_shield_attachments_message",
        "channel_shield_attachments",
        ["message_id"],
    )

    op.create_table(
        "channel_shield_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), nullable=True),
        sa.Column("protection_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_channel_shield_events_message",
        "channel_shield_events",
        ["message_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_channel_shield_events_message", table_name="channel_shield_events")
    op.drop_table("channel_shield_events")
    op.drop_index("ix_channel_shield_attachments_message", table_name="channel_shield_attachments")
    op.drop_table("channel_shield_attachments")
    op.drop_index("ix_channel_shield_messages_channel", table_name="channel_shield_messages")
    op.drop_index("ix_channel_shield_messages_user_status", table_name="channel_shield_messages")
    op.drop_table("channel_shield_messages")
    op.drop_index("ix_channel_shield_protections_key", table_name="channel_shield_protections")
    op.drop_index("ix_channel_shield_protections_user_channel", table_name="channel_shield_protections")
    op.drop_table("channel_shield_protections")

"""Alembic migration: App Foundation SDK tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005_app_foundation_sdk"
down_revision = "004_developer_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sdk_apps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("domain_schema", sa.JSON(), nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("api_token_id", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "sdk_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("app_id", sa.String(length=36), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_response", sa.JSON(), nullable=True),
    )
    op.create_index("ix_sdk_plans_app_status", "sdk_plans", ["app_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_sdk_plans_app_status", table_name="sdk_plans")
    op.drop_table("sdk_plans")
    op.drop_table("sdk_apps")

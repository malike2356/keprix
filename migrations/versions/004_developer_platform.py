"""Alembic migration: developer API keys and webhooks."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "004_developer_platform"
down_revision = "003_metrics_request_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "developer_api_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("workspace_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("role", sa.Text(), nullable=False, server_default="developer"),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("allowed_models", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("allowed_endpoints", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("monthly_limit", sa.Integer(), nullable=True),
        sa.Column("usage_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_developer_api_keys_workspace", "developer_api_keys", ["workspace_id"])
    op.create_index("ix_developer_api_keys_prefix", "developer_api_keys", ["key_prefix"])

    op.create_table(
        "developer_webhooks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret_hash", sa.Text(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "developer_api_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("api_key_id", sa.Text(), nullable=True),
        sa.Column("workspace_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Numeric(), nullable=False),
        sa.Column("request_body_redacted", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_developer_api_logs_recorded", "developer_api_logs", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_developer_api_logs_recorded", table_name="developer_api_logs")
    op.drop_table("developer_api_logs")
    op.drop_table("developer_webhooks")
    op.drop_index("ix_developer_api_keys_prefix", table_name="developer_api_keys")
    op.drop_index("ix_developer_api_keys_workspace", table_name="developer_api_keys")
    op.drop_table("developer_api_keys")

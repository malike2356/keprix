"""Vault items and OAuth column additions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "004_vault_oauth"
down_revision = "003_email_contacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vault_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False, server_default="password"),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("value_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_vault_items_user_category", "vault_items", ["user_id", "category"])

    op.add_column("email_accounts", sa.Column("oauth_provider", sa.Text(), nullable=True))
    op.add_column("email_accounts", sa.Column("oauth_vault_item_id", sa.String(length=36), nullable=True))
    op.add_column("contact_sync_sources", sa.Column("sync_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("contact_sync_sources", "sync_token")
    op.drop_column("email_accounts", "oauth_vault_item_id")
    op.drop_column("email_accounts", "oauth_provider")
    op.drop_index("ix_vault_items_user_category", table_name="vault_items")
    op.drop_table("vault_items")

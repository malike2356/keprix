"""Email and contacts tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "003_email_contacts"
down_revision = "002_research_playbook_compare"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "email_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False, server_default="Default"),
        sa.Column("email_address", sa.Text(), nullable=False),
        sa.Column("imap_host", sa.Text(), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("smtp_host", sa.Text(), nullable=False),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("use_starttls", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "emails",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("email_accounts.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("message_id", sa.Text(), nullable=False),
        sa.Column("uid", sa.BigInteger(), nullable=True),
        sa.Column("folder", sa.Text(), nullable=False, server_default="INBOX"),
        sa.Column("from_address", sa.Text(), nullable=False),
        sa.Column("from_name", sa.Text(), nullable=True),
        sa.Column("to_addresses", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("cc_addresses", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("subject", sa.Text(), nullable=False, server_default=""),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("preview", sa.Text(), nullable=True),
        sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_starred", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_trashed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_tags", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("ai_priority", sa.Text(), nullable=False, server_default="normal"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("account_id", "uid", "folder", name="uq_emails_account_uid_folder"),
    )
    op.create_index("ix_emails_user_read_received", "emails", ["user_id", "is_read", "received_at"])

    op.create_table(
        "email_drafts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("email_accounts.id"), nullable=True),
        sa.Column("reply_to_email_id", sa.String(length=36), sa.ForeignKey("emails.id"), nullable=True),
        sa.Column("to_addresses", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("cc_addresses", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("subject", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "contacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("given_name", sa.Text(), nullable=True),
        sa.Column("family_name", sa.Text(), nullable=True),
        sa.Column("emails", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("phones", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("addresses", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("organisation", sa.Text(), nullable=True),
        sa.Column("job_title", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("source_id", sa.Text(), nullable=True),
        sa.Column("source_etag", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("source", "source_id", name="uq_contacts_source_source_id"),
    )
    op.create_index("ix_contacts_display_name", "contacts", ["display_name"])

    op.create_table(
        "contact_sync_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("vault_token_id", sa.String(length=36), nullable=True),
        sa.Column("carddav_url", sa.Text(), nullable=True),
        sa.Column("carddav_username", sa.Text(), nullable=True),
        sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_full_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delta_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("contact_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "contact_action_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False, unique=True),
        sa.Column("confirm_before_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("confirm_before_call", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("read_back_draft", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("contact_action_preferences")
    op.drop_table("contact_sync_sources")
    op.drop_index("ix_contacts_display_name", table_name="contacts")
    op.drop_table("contacts")
    op.drop_table("email_drafts")
    op.drop_index("ix_emails_user_read_received", table_name="emails")
    op.drop_table("emails")
    op.drop_table("email_accounts")

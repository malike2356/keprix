"""SQLAlchemy ORM models for email, contacts, and vault."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from keprix.database import Base


class EmailAccountRow(Base):
    __tablename__ = "email_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False, server_default="Default")
    email_address: Mapped[str] = mapped_column(Text, nullable=False)
    imap_host: Mapped[str] = mapped_column(Text, nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, server_default="993")
    smtp_host: Mapped[str] = mapped_column(Text, nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, server_default="587")
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    use_starttls: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    oauth_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_vault_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailRow(Base):
    __tablename__ = "emails"
    __table_args__ = (UniqueConstraint("account_id", "uid", "folder", name="uq_emails_account_uid_folder"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_accounts.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[str] = mapped_column(Text, nullable=False)
    uid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    folder: Mapped[str] = mapped_column(Text, nullable=False, server_default="INBOX")
    from_address: Mapped[str] = mapped_column(Text, nullable=False)
    from_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    subject: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_trashed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    ai_priority: Mapped[str] = mapped_column(Text, nullable=False, server_default="normal")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailDraftRow(Base):
    __tablename__ = "email_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("email_accounts.id"), nullable=True)
    reply_to_email_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("emails.id"), nullable=True)
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    subject: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContactRow(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("user_id", "source", "source_id", name="uq_contacts_user_source_source_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    given_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    emails: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    phones: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    addresses: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    organisation: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    source_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_etag: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContactSyncSourceRow(Base):
    __tablename__ = "contact_sync_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    vault_token_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    carddav_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    carddav_username: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    last_full_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_delta_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContactActionPreferencesRow(Base):
    __tablename__ = "contact_action_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    confirm_before_email: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    confirm_before_call: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    read_back_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VaultItemRow(Base):
    __tablename__ = "vault_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, server_default="password")
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

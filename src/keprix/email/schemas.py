"""Pydantic schemas for the email API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EmailAccountCreate(BaseModel):
    label: str = "Default"
    email_address: str
    imap_host: str
    imap_port: int = 993
    smtp_host: str
    smtp_port: int = 587
    username: str
    password: str
    use_tls: bool = True
    use_starttls: bool = False
    poll_interval_seconds: int = 60


class EmailAccountUpdate(BaseModel):
    label: str | None = None
    email_address: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    username: str | None = None
    password: str | None = None
    use_tls: bool | None = None
    use_starttls: bool | None = None
    poll_interval_seconds: int | None = None
    is_active: bool | None = None


class EmailAccountOut(BaseModel):
    id: str
    user_id: str
    label: str
    email_address: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    username: str
    use_tls: bool
    use_starttls: bool
    poll_interval_seconds: int
    last_polled_at: datetime | None
    is_active: bool
    created_at: datetime


class EmailOut(BaseModel):
    id: str
    account_id: str
    user_id: str
    message_id: str
    uid: int | None
    folder: str
    from_address: str
    from_name: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str
    body_text: str | None
    body_html: str | None
    preview: str | None
    has_attachments: bool
    is_read: bool
    is_starred: bool
    is_trashed: bool
    ai_summary: str | None
    ai_tags: list[str]
    ai_priority: str
    received_at: datetime
    created_at: datetime


class EmailDraftCreate(BaseModel):
    account_id: str | None = None
    reply_to_email_id: str | None = None
    to_addresses: list[str] = Field(default_factory=list)
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str = ""
    body: str = ""


class EmailDraftUpdate(BaseModel):
    to_addresses: list[str] | None = None
    cc_addresses: list[str] | None = None
    subject: str | None = None
    body: str | None = None


class EmailDraftOut(BaseModel):
    id: str
    user_id: str
    account_id: str | None
    reply_to_email_id: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str
    body: str
    is_ai_generated: bool
    created_at: datetime
    updated_at: datetime


class SendEmailBody(BaseModel):
    account_id: str | None = None
    to_addresses: list[str]
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str
    body: str


class AiSummaryOut(BaseModel):
    summary: str


class SyncStatusOut(BaseModel):
    accounts: list[dict[str, Any]]

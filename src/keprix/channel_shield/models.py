"""SQLAlchemy models for Channel Shield (migrations 020 + 021)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from keprix.database import Base


class ChannelShieldProtectionRow(Base):
    __tablename__ = "channel_shield_protections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    protection_key: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChannelShieldMessageRow(Base):
    __tablename__ = "channel_shield_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    protection_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    external_message_id: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_addr: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_addrs: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    envelope: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    safe_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_blob_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    scout_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    agent_safe_content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    policy_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChannelShieldAttachmentRow(Base):
    __tablename__ = "channel_shield_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(36), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    blob_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChannelShieldEventRow(Base):
    __tablename__ = "channel_shield_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    protection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

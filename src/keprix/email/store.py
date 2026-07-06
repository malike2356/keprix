"""In-memory email persistence (PostgreSQL schema in migrations/003)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.email.crypto import decrypt_secret, encrypt_secret


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EmailAccountRecord:
    id: str
    user_id: str
    label: str
    email_address: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    username: str
    password_encrypted: str
    use_tls: bool
    use_starttls: bool
    poll_interval_seconds: int
    last_polled_at: datetime | None
    is_active: bool
    created_at: datetime
    oauth_provider: str | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "email_address": self.email_address,
            "imap_host": self.imap_host,
            "imap_port": self.imap_port,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "username": self.username,
            "use_tls": self.use_tls,
            "use_starttls": self.use_starttls,
            "poll_interval_seconds": self.poll_interval_seconds,
            "last_polled_at": self.last_polled_at,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    def to_connection(self) -> dict[str, Any]:
        return {
            **self.to_public(),
            "password_encrypted": self.password_encrypted,
        }


@dataclass
class EmailRecord:
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "message_id": self.message_id,
            "uid": self.uid,
            "folder": self.folder,
            "from_address": self.from_address,
            "from_name": self.from_name,
            "to_addresses": self.to_addresses,
            "cc_addresses": self.cc_addresses,
            "subject": self.subject,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "preview": self.preview,
            "has_attachments": self.has_attachments,
            "is_read": self.is_read,
            "is_starred": self.is_starred,
            "is_trashed": self.is_trashed,
            "ai_summary": self.ai_summary,
            "ai_tags": self.ai_tags,
            "ai_priority": self.ai_priority,
            "received_at": self.received_at,
            "created_at": self.created_at,
        }


@dataclass
class EmailDraftRecord:
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "reply_to_email_id": self.reply_to_email_id,
            "to_addresses": self.to_addresses,
            "cc_addresses": self.cc_addresses,
            "subject": self.subject,
            "body": self.body,
            "is_ai_generated": self.is_ai_generated,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EmailStore:
    def __init__(self) -> None:
        self._accounts: dict[str, EmailAccountRecord] = {}
        self._emails: dict[str, EmailRecord] = {}
        self._drafts: dict[str, EmailDraftRecord] = {}
        self._lock = asyncio.Lock()

    async def create_account(self, user_id: str, data: dict[str, Any]) -> EmailAccountRecord:
        from keprix.db.email_repo import pg_create_account

        pg_record = await pg_create_account(user_id, data)
        if pg_record is not None:
            async with self._lock:
                self._accounts[pg_record.id] = pg_record
            return pg_record
        account_id = str(uuid.uuid4())
        now = _utcnow()
        record = EmailAccountRecord(
            id=account_id,
            user_id=user_id,
            label=data.get("label", "Default"),
            email_address=data["email_address"],
            imap_host=data["imap_host"],
            imap_port=int(data.get("imap_port", 993)),
            smtp_host=data["smtp_host"],
            smtp_port=int(data.get("smtp_port", 587)),
            username=data["username"],
            password_encrypted=encrypt_secret(data["password"]),
            use_tls=bool(data.get("use_tls", True)),
            use_starttls=bool(data.get("use_starttls", False)),
            poll_interval_seconds=int(data.get("poll_interval_seconds", 60)),
            last_polled_at=None,
            is_active=True,
            created_at=now,
        )
        async with self._lock:
            self._accounts[account_id] = record
        return record

    async def list_accounts(self, user_id: str) -> list[EmailAccountRecord]:
        from keprix.db.email_repo import pg_list_accounts

        pg_rows = await pg_list_accounts(user_id)
        if pg_rows is not None:
            async with self._lock:
                for row in pg_rows:
                    self._accounts[row.id] = row
            return pg_rows
        return [a for a in self._accounts.values() if a.user_id == user_id]

    async def get_account(self, account_id: str, user_id: str) -> EmailAccountRecord | None:
        record = self._accounts.get(account_id)
        if record is None or record.user_id != user_id:
            return None
        return record

    async def update_account(
        self, account_id: str, user_id: str, updates: dict[str, Any]
    ) -> EmailAccountRecord | None:
        async with self._lock:
            record = self._accounts.get(account_id)
            if record is None or record.user_id != user_id:
                return None
            for key, value in updates.items():
                if value is None:
                    continue
                if key == "password":
                    record.password_encrypted = encrypt_secret(value)
                elif hasattr(record, key):
                    setattr(record, key, value)
            self._accounts[account_id] = record
            return record

    async def delete_account(self, account_id: str, user_id: str) -> bool:
        async with self._lock:
            record = self._accounts.get(account_id)
            if record is None or record.user_id != user_id:
                return False
            del self._accounts[account_id]
            self._emails = {
                k: v for k, v in self._emails.items() if v.account_id != account_id
            }
            return True

    async def list_active_accounts(self) -> list[EmailAccountRecord]:
        from keprix.db.email_repo import pg_list_active_accounts

        pg_rows = await pg_list_active_accounts()
        if pg_rows is not None:
            async with self._lock:
                for row in pg_rows:
                    self._accounts[row.id] = row
            return pg_rows
        return [a for a in self._accounts.values() if a.is_active]

    async def touch_polled(self, account_id: str) -> None:
        async with self._lock:
            record = self._accounts.get(account_id)
            if record:
                record.last_polled_at = _utcnow()

    async def upsert_email(self, account: EmailAccountRecord, parsed: dict[str, Any]) -> EmailRecord | None:
        key = (account.id, parsed.get("uid"), parsed.get("folder", "INBOX"))
        async with self._lock:
            for existing in self._emails.values():
                if (
                    existing.account_id == key[0]
                    and existing.uid == key[1]
                    and existing.folder == key[2]
                ):
                    return None
            email_id = str(uuid.uuid4())
            now = _utcnow()
            record = EmailRecord(
                id=email_id,
                account_id=account.id,
                user_id=account.user_id,
                message_id=parsed["message_id"],
                uid=parsed.get("uid"),
                folder=parsed.get("folder", "INBOX"),
                from_address=parsed["from_address"],
                from_name=parsed.get("from_name"),
                to_addresses=parsed.get("to_addresses", []),
                cc_addresses=parsed.get("cc_addresses", []),
                subject=parsed.get("subject", ""),
                body_text=parsed.get("body_text"),
                body_html=parsed.get("body_html"),
                preview=parsed.get("preview"),
                has_attachments=bool(parsed.get("has_attachments")),
                is_read=False,
                is_starred=False,
                is_trashed=False,
                ai_summary=None,
                ai_tags=[],
                ai_priority="normal",
                received_at=parsed.get("received_at", now),
                created_at=now,
            )
            self._emails[email_id] = record
            return record

    async def list_emails(
        self,
        user_id: str,
        *,
        unread: bool | None = None,
        starred: bool | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmailRecord]:
        rows = [e for e in self._emails.values() if e.user_id == user_id and not e.is_trashed]
        if unread is True:
            rows = [e for e in rows if not e.is_read]
        if starred is True:
            rows = [e for e in rows if e.is_starred]
        if tag:
            rows = [e for e in rows if tag in e.ai_tags]
        rows.sort(key=lambda e: e.received_at, reverse=True)
        return rows[offset : offset + limit]

    async def get_email(self, email_id: str, user_id: str) -> EmailRecord | None:
        record = self._emails.get(email_id)
        if record is None or record.user_id != user_id:
            return None
        return record

    async def update_email(
        self, email_id: str, user_id: str, updates: dict[str, Any]
    ) -> EmailRecord | None:
        async with self._lock:
            record = self._emails.get(email_id)
            if record is None or record.user_id != user_id:
                return None
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            return record

    async def search_emails(self, user_id: str, query: str, limit: int = 50) -> list[EmailRecord]:
        q = query.lower()
        rows = [
            e
            for e in self._emails.values()
            if e.user_id == user_id
            and not e.is_trashed
            and (
                q in (e.subject or "").lower()
                or q in (e.body_text or "").lower()
                or any(q in t.lower() for t in e.ai_tags)
            )
        ]
        rows.sort(key=lambda e: e.received_at, reverse=True)
        return rows[:limit]

    async def create_draft(self, user_id: str, data: dict[str, Any]) -> EmailDraftRecord:
        draft_id = str(uuid.uuid4())
        now = _utcnow()
        record = EmailDraftRecord(
            id=draft_id,
            user_id=user_id,
            account_id=data.get("account_id"),
            reply_to_email_id=data.get("reply_to_email_id"),
            to_addresses=data.get("to_addresses", []),
            cc_addresses=data.get("cc_addresses", []),
            subject=data.get("subject", ""),
            body=data.get("body", ""),
            is_ai_generated=bool(data.get("is_ai_generated", False)),
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._drafts[draft_id] = record
        return record

    async def list_drafts(self, user_id: str) -> list[EmailDraftRecord]:
        return [d for d in self._drafts.values() if d.user_id == user_id]

    async def get_draft(self, draft_id: str, user_id: str) -> EmailDraftRecord | None:
        record = self._drafts.get(draft_id)
        if record is None or record.user_id != user_id:
            return None
        return record

    async def update_draft(
        self, draft_id: str, user_id: str, updates: dict[str, Any]
    ) -> EmailDraftRecord | None:
        async with self._lock:
            record = self._drafts.get(draft_id)
            if record is None or record.user_id != user_id:
                return None
            for key, value in updates.items():
                if value is not None and hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = _utcnow()
            return record

    async def delete_draft(self, draft_id: str, user_id: str) -> bool:
        async with self._lock:
            record = self._drafts.get(draft_id)
            if record is None or record.user_id != user_id:
                return False
            del self._drafts[draft_id]
            return True


_store: EmailStore | None = None


def get_email_store() -> EmailStore:
    global _store
    if _store is None:
        _store = EmailStore()
    return _store


def reset_email_store() -> None:
    global _store
    _store = EmailStore()

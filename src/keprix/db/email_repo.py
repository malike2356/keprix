"""PostgreSQL persistence for email entities."""

from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, TypeVar

from sqlalchemy import select

from keprix.database import get_session_factory
from keprix.db.models import EmailAccountRow, EmailDraftRow, EmailRow
from keprix.email.store import EmailAccountRecord, EmailDraftRecord, EmailRecord

logger = logging.getLogger(__name__)
T = TypeVar("T")


def postgres_configured() -> bool:
    """True only when an operator set a database URL. The settings default is not enough."""
    return bool(os.environ.get("KEPRIX_DATABASE_URL") or os.environ.get("DATABASE_URL"))


def _use_db() -> bool:
    if "pytest" in sys.modules:
        return False
    if not postgres_configured():
        return False
    return get_session_factory() is not None


async def _optional_pg(factory: Callable[[], Awaitable[T]], fallback: T) -> T:
    if not _use_db():
        return fallback
    try:
        return await factory()
    except Exception as exc:
        logger.warning("Postgres email store unavailable (%s); using local file store", exc)
        return fallback


def _account_from_row(row: EmailAccountRow) -> EmailAccountRecord:
    return EmailAccountRecord(
        id=row.id,
        user_id=row.user_id,
        label=row.label,
        email_address=row.email_address,
        imap_host=row.imap_host,
        imap_port=row.imap_port,
        smtp_host=row.smtp_host,
        smtp_port=row.smtp_port,
        username=row.username,
        password_encrypted=row.password_encrypted,
        use_tls=row.use_tls,
        use_starttls=row.use_starttls,
        poll_interval_seconds=row.poll_interval_seconds,
        last_polled_at=row.last_polled_at,
        is_active=row.is_active,
        created_at=row.created_at,
        oauth_provider=getattr(row, "oauth_provider", None),
        oauth_vault_item_id=getattr(row, "oauth_vault_item_id", None),
    )


def _email_from_row(row: EmailRow) -> EmailRecord:
    return EmailRecord(
        id=row.id,
        account_id=row.account_id,
        user_id=row.user_id,
        message_id=row.message_id,
        uid=row.uid,
        folder=row.folder,
        from_address=row.from_address,
        from_name=row.from_name,
        to_addresses=list(row.to_addresses or []),
        cc_addresses=list(row.cc_addresses or []),
        subject=row.subject,
        body_text=row.body_text,
        body_html=row.body_html,
        preview=row.preview,
        has_attachments=row.has_attachments,
        is_read=row.is_read,
        is_starred=row.is_starred,
        is_trashed=row.is_trashed,
        ai_summary=row.ai_summary,
        ai_tags=list(row.ai_tags or []),
        ai_priority=row.ai_priority,
        received_at=row.received_at,
        created_at=row.created_at,
    )


async def pg_create_account(user_id: str, data: dict) -> EmailAccountRecord | None:
    from keprix.email.crypto import encrypt_secret

    async def _run() -> EmailAccountRecord | None:
        factory = get_session_factory()
        assert factory is not None
        account_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        async with factory() as session:
            row = EmailAccountRow(
                id=account_id,
                user_id=user_id,
                label=data.get("label", "Default"),
                email_address=data["email_address"],
                imap_host=data["imap_host"],
                imap_port=int(data.get("imap_port", 993)),
                smtp_host=data["smtp_host"],
                smtp_port=int(data.get("smtp_port", 587)),
                username=data["username"],
                password_encrypted=encrypt_secret(data.get("password", "")),
                use_tls=bool(data.get("use_tls", True)),
                use_starttls=bool(data.get("use_starttls", False)),
                poll_interval_seconds=int(data.get("poll_interval_seconds", 300)),
                is_active=True,
                oauth_provider=data.get("oauth_provider"),
                oauth_vault_item_id=data.get("oauth_vault_item_id"),
                created_at=now,
            )
            session.add(row)
            await session.commit()
            return _account_from_row(row)

    return await _optional_pg(_run, None)


async def pg_update_account(account_id: str, user_id: str, updates: dict) -> EmailAccountRecord | None:
    from keprix.email.crypto import encrypt_secret

    async def _run() -> EmailAccountRecord | None:
        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            row = await session.get(EmailAccountRow, account_id)
            if row is None or row.user_id != user_id:
                return None
            for key, value in updates.items():
                if value is None:
                    continue
                if key == "password":
                    row.password_encrypted = encrypt_secret(value)
                elif hasattr(row, key):
                    setattr(row, key, value)
            await session.commit()
            await session.refresh(row)
            return _account_from_row(row)

    return await _optional_pg(_run, None)


async def pg_delete_account(account_id: str, user_id: str) -> bool:
    async def _run() -> bool:
        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            row = await session.get(EmailAccountRow, account_id)
            if row is None or row.user_id != user_id:
                return False
            await session.delete(row)
            await session.commit()
            return True

    return await _optional_pg(_run, False)


async def pg_touch_polled(account_id: str) -> None:
    async def _run() -> None:
        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            row = await session.get(EmailAccountRow, account_id)
            if row is None:
                return
            row.last_polled_at = datetime.now(timezone.utc)
            await session.commit()

    await _optional_pg(_run, None)


async def pg_list_accounts(user_id: str) -> list[EmailAccountRecord] | None:
    async def _run() -> list[EmailAccountRecord] | None:
        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            rows = (
                await session.execute(
                    select(EmailAccountRow).where(EmailAccountRow.user_id == user_id)
                )
            ).scalars().all()
            return [_account_from_row(r) for r in rows]

    return await _optional_pg(_run, None)


async def pg_get_account(account_id: str, user_id: str) -> EmailAccountRecord | None:
    async def _run() -> EmailAccountRecord | None:
        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            row = await session.get(EmailAccountRow, account_id)
            if row is None or row.user_id != user_id:
                return None
            return _account_from_row(row)

    return await _optional_pg(_run, None)


async def pg_list_active_accounts() -> list[EmailAccountRecord] | None:
    async def _run() -> list[EmailAccountRecord] | None:
        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            rows = (
                await session.execute(
                    select(EmailAccountRow).where(EmailAccountRow.is_active.is_(True))
                )
            ).scalars().all()
            return [_account_from_row(r) for r in rows]

    return await _optional_pg(_run, None)

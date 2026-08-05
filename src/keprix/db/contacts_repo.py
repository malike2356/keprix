"""PostgreSQL persistence for contacts and sync sources."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from keprix.database import get_session_factory
from keprix.db.models import ContactActionPreferencesRow, ContactRow, ContactSyncSourceRow


def _use_db() -> bool:
    if "pytest" in sys.modules:
        return False
    return get_session_factory() is not None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def contact_from_row(row: ContactRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "display_name": row.display_name,
        "given_name": row.given_name,
        "family_name": row.family_name,
        "emails": list(row.emails or []),
        "phones": list(row.phones or []),
        "addresses": list(row.addresses or []),
        "organisation": row.organisation,
        "job_title": row.job_title,
        "notes": row.notes,
        "photo_url": row.photo_url,
        "source": row.source,
        "source_id": row.source_id,
        "source_etag": row.source_etag,
        "last_synced_at": row.last_synced_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def source_from_row(row: ContactSyncSourceRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "provider": row.provider,
        "display_name": row.display_name,
        "vault_token_id": row.vault_token_id,
        "carddav_url": row.carddav_url,
        "carddav_username": row.carddav_username,
        "sync_enabled": bool(row.sync_enabled),
        "sync_interval_minutes": int(row.sync_interval_minutes or 60),
        "last_full_sync_at": _iso(row.last_full_sync_at),
        "last_delta_sync_at": _iso(row.last_delta_sync_at),
        "sync_token": row.sync_token,
        "last_sync_error": row.last_sync_error,
        "contact_count": int(row.contact_count or 0),
        "created_at": _iso(row.created_at),
    }


async def pg_create_contact(user_id: str, data: dict[str, Any], *, source: str = "manual") -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    now = _utcnow()
    contact_id = str(data.get("id") or uuid.uuid4())
    async with factory() as session:
        row = ContactRow(
            id=contact_id,
            user_id=user_id,
            display_name=data["display_name"],
            given_name=data.get("given_name"),
            family_name=data.get("family_name"),
            emails=list(data.get("emails") or []),
            phones=list(data.get("phones") or []),
            addresses=list(data.get("addresses") or []),
            organisation=data.get("organisation"),
            job_title=data.get("job_title"),
            notes=data.get("notes"),
            photo_url=data.get("photo_url"),
            source=source,
            source_id=data.get("source_id"),
            source_etag=data.get("source_etag"),
            last_synced_at=_parse_dt(data.get("last_synced_at")),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return contact_from_row(row)


async def pg_list_contacts(
    user_id: str, *, query: str | None = None, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        rows = (
            await session.execute(select(ContactRow).where(ContactRow.user_id == user_id))
        ).scalars().all()
        items = [contact_from_row(r) for r in rows]
        if query:
            q = query.lower()
            items = [
                c
                for c in items
                if q in c["display_name"].lower()
                or q in (c.get("organisation") or "").lower()
                or any(q in (e.get("address") or "").lower() for e in (c.get("emails") or []))
            ]
        items.sort(
            key=lambda c: (c.get("family_name") or "", c.get("given_name") or "", c["display_name"])
        )
        return items[offset : offset + limit]


async def pg_get_contact(contact_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = await session.get(ContactRow, contact_id)
        if row is None:
            return None
        if user_id is not None and row.user_id != user_id:
            return None
        return contact_from_row(row)


async def pg_update_contact(
    contact_id: str, user_id: str, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = await session.get(ContactRow, contact_id)
        if row is None or row.user_id != user_id:
            return None
        if row.source != "manual":
            return None
        for key, value in updates.items():
            if value is not None and hasattr(row, key) and key not in {"id", "user_id", "source"}:
                setattr(row, key, value)
        row.updated_at = _utcnow()
        await session.commit()
        await session.refresh(row)
        return contact_from_row(row)


async def pg_delete_contact(contact_id: str, user_id: str) -> bool | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = await session.get(ContactRow, contact_id)
        if row is None or row.user_id != user_id:
            return False
        if row.source != "manual":
            return False
        await session.delete(row)
        await session.commit()
        return True


async def pg_find_by_email(user_id: str, address: str) -> dict[str, Any] | None:
    if not _use_db():
        return None
    needle = address.lower().strip()
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        rows = (
            await session.execute(select(ContactRow).where(ContactRow.user_id == user_id))
        ).scalars().all()
        for row in rows:
            for email in row.emails or []:
                if (email.get("address") or "").lower() == needle:
                    return contact_from_row(row)
    return None


async def pg_find_by_source(
    user_id: str, source: str, source_id: str
) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = (
            await session.execute(
                select(ContactRow).where(
                    ContactRow.user_id == user_id,
                    ContactRow.source == source,
                    ContactRow.source_id == source_id,
                )
            )
        ).scalar_one_or_none()
        return contact_from_row(row) if row else None


async def pg_upsert_import(
    user_id: str, data: dict[str, Any], *, source: str, match_email: str | None = None
) -> tuple[dict[str, Any], str] | None:
    if not _use_db():
        return None
    existing = None
    source_id = data.get("source_id")
    if source_id:
        existing = await pg_find_by_source(user_id, source, str(source_id))
    if existing is None and match_email:
        existing = await pg_find_by_email(user_id, match_email)
    if existing:
        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            row = await session.get(ContactRow, existing["id"])
            if row is None or row.user_id != user_id:
                return None
            for key in (
                "display_name",
                "given_name",
                "family_name",
                "emails",
                "phones",
                "addresses",
                "organisation",
                "job_title",
                "notes",
                "source_id",
                "source_etag",
            ):
                if key in data and data[key] is not None:
                    setattr(row, key, data[key])
            row.source = source
            row.last_synced_at = _utcnow()
            row.updated_at = _utcnow()
            await session.commit()
            await session.refresh(row)
            return contact_from_row(row), "updated"
    created = await pg_create_contact(user_id, {**data, "last_synced_at": _utcnow()}, source=source)
    if created is None:
        return None
    return created, "added"


async def pg_all_contacts(user_id: str | None = None) -> list[dict[str, Any]] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        stmt = select(ContactRow)
        if user_id is not None:
            stmt = stmt.where(ContactRow.user_id == user_id)
        rows = (await session.execute(stmt)).scalars().all()
        return [contact_from_row(r) for r in rows]


async def pg_get_preferences(user_id: str) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = (
            await session.execute(
                select(ContactActionPreferencesRow).where(
                    ContactActionPreferencesRow.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            now = _utcnow()
            row = ContactActionPreferencesRow(
                id=str(uuid.uuid4()),
                user_id=user_id,
                confirm_before_email=True,
                confirm_before_call=True,
                read_back_draft=True,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {
            "user_id": row.user_id,
            "confirm_before_email": row.confirm_before_email,
            "confirm_before_call": row.confirm_before_call,
            "read_back_draft": row.read_back_draft,
            "updated_at": row.updated_at,
        }


async def pg_update_preferences(user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not _use_db():
        return None
    prefs = await pg_get_preferences(user_id)
    if prefs is None:
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = (
            await session.execute(
                select(ContactActionPreferencesRow).where(
                    ContactActionPreferencesRow.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return prefs
        for key, value in updates.items():
            if value is not None and hasattr(row, key) and key != "user_id":
                setattr(row, key, value)
        row.updated_at = _utcnow()
        await session.commit()
        await session.refresh(row)
        return {
            "user_id": row.user_id,
            "confirm_before_email": row.confirm_before_email,
            "confirm_before_call": row.confirm_before_call,
            "read_back_draft": row.read_back_draft,
            "updated_at": row.updated_at,
        }


async def pg_upsert_sync_source(source: dict[str, Any]) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    source_id = str(source["id"])
    async with factory() as session:
        row = await session.get(ContactSyncSourceRow, source_id)
        if row is None:
            row = ContactSyncSourceRow(
                id=source_id,
                user_id=str(source.get("user_id") or "local"),
                provider=source["provider"],
                display_name=source["display_name"],
                vault_token_id=source.get("vault_token_id"),
                carddav_url=source.get("carddav_url"),
                carddav_username=source.get("carddav_username"),
                sync_enabled=bool(source.get("sync_enabled", True)),
                sync_interval_minutes=int(source.get("sync_interval_minutes") or 60),
                last_full_sync_at=_parse_dt(source.get("last_full_sync_at")),
                last_delta_sync_at=_parse_dt(source.get("last_delta_sync_at")),
                sync_token=source.get("sync_token"),
                last_sync_error=source.get("last_sync_error"),
                contact_count=int(source.get("contact_count") or 0),
                created_at=_utcnow(),
            )
            session.add(row)
        else:
            for key in (
                "display_name",
                "vault_token_id",
                "carddav_url",
                "carddav_username",
                "sync_enabled",
                "sync_interval_minutes",
                "sync_token",
                "last_sync_error",
                "contact_count",
            ):
                if key in source:
                    setattr(row, key, source[key])
            if "last_full_sync_at" in source:
                row.last_full_sync_at = _parse_dt(source.get("last_full_sync_at"))
            if "last_delta_sync_at" in source:
                row.last_delta_sync_at = _parse_dt(source.get("last_delta_sync_at"))
        await session.commit()
        await session.refresh(row)
        return source_from_row(row)


async def pg_list_sync_sources(user_id: str | None = None) -> list[dict[str, Any]] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        stmt = select(ContactSyncSourceRow)
        if user_id is not None:
            stmt = stmt.where(ContactSyncSourceRow.user_id == user_id)
        rows = (await session.execute(stmt)).scalars().all()
        return [source_from_row(r) for r in rows]


async def pg_get_sync_source(source_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = await session.get(ContactSyncSourceRow, source_id)
        if row is None:
            return None
        if user_id is not None and row.user_id != user_id:
            return None
        return source_from_row(row)


async def pg_delete_sync_source(source_id: str, user_id: str | None = None) -> bool | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = await session.get(ContactSyncSourceRow, source_id)
        if row is None:
            return False
        if user_id is not None and row.user_id != user_id:
            return False
        await session.delete(row)
        await session.commit()
        return True

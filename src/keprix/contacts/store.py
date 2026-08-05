"""Contact store with Postgres when available, in-memory for tests."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


SYNCED_SOURCES = frozenset({"google", "microsoft", "carddav", "vcf", "csv"})


@dataclass
class ContactRecord:
    id: str
    user_id: str
    display_name: str
    given_name: str | None
    family_name: str | None
    emails: list[dict[str, Any]]
    phones: list[dict[str, Any]]
    addresses: list[dict[str, Any]]
    organisation: str | None
    job_title: str | None
    notes: str | None
    photo_url: str | None
    source: str
    source_id: str | None
    source_etag: str | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tenant_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "given_name": self.given_name,
            "family_name": self.family_name,
            "emails": self.emails,
            "phones": self.phones,
            "addresses": self.addresses,
            "organisation": self.organisation,
            "job_title": self.job_title,
            "notes": self.notes,
            "photo_url": self.photo_url,
            "source": self.source,
            "source_id": self.source_id,
            "last_synced_at": self.last_synced_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "editable": self.source == "manual",
            "tenant_id": self.tenant_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContactRecord:
        return cls(
            id=data["id"],
            user_id=str(data.get("user_id") or "local"),
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
            source=data.get("source") or "manual",
            source_id=data.get("source_id"),
            source_etag=data.get("source_etag"),
            last_synced_at=data.get("last_synced_at"),
            created_at=data.get("created_at") or _utcnow(),
            updated_at=data.get("updated_at") or _utcnow(),
            tenant_id=data.get("tenant_id"),
        )


@dataclass
class ContactPreferencesRecord:
    user_id: str
    confirm_before_email: bool = True
    confirm_before_call: bool = True
    read_back_draft: bool = True
    updated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "confirm_before_email": self.confirm_before_email,
            "confirm_before_call": self.confirm_before_call,
            "read_back_draft": self.read_back_draft,
            "updated_at": self.updated_at,
        }


class ContactStore:
    def __init__(self) -> None:
        self._contacts: dict[str, ContactRecord] = {}
        self._preferences: dict[str, ContactPreferencesRecord] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, data: dict[str, Any], *, source: str = "manual", user_id: str = "local"
    ) -> ContactRecord:
        from keprix.db.contacts_repo import _use_db, pg_create_contact

        if _use_db():
            pg_row = await pg_create_contact(user_id, data, source=source)
            if pg_row is None:
                raise RuntimeError("Failed to persist contact")
            return ContactRecord.from_dict(pg_row)

        now = _utcnow()
        contact_id = str(uuid.uuid4())
        record = ContactRecord(
            id=contact_id,
            user_id=user_id,
            display_name=data["display_name"],
            given_name=data.get("given_name"),
            family_name=data.get("family_name"),
            emails=[e if isinstance(e, dict) else e for e in data.get("emails", [])],
            phones=[p if isinstance(p, dict) else p for p in data.get("phones", [])],
            addresses=[a if isinstance(a, dict) else a for a in data.get("addresses", [])],
            organisation=data.get("organisation"),
            job_title=data.get("job_title"),
            notes=data.get("notes"),
            photo_url=data.get("photo_url"),
            source=source,
            source_id=data.get("source_id"),
            source_etag=data.get("source_etag"),
            last_synced_at=data.get("last_synced_at"),
            created_at=now,
            updated_at=now,
            tenant_id=data.get("tenant_id") or self._stamp_tenant(),
        )
        async with self._lock:
            self._contacts[contact_id] = record
        return record

    def _stamp_tenant(self) -> str | None:
        try:
            from keprix.tenancy.isolation import current_tenant_id

            return current_tenant_id()
        except Exception:
            return None

    async def list_contacts(
        self,
        *,
        user_id: str = "local",
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ContactRecord]:
        from keprix.db.contacts_repo import _use_db, pg_list_contacts

        if _use_db():
            pg_rows = await pg_list_contacts(user_id, query=query, limit=limit, offset=offset) or []
            return [ContactRecord.from_dict(r) for r in pg_rows]

        rows = [c for c in self._contacts.values() if c.user_id == user_id]
        try:
            from keprix.tenancy.isolation import assert_tenant_owns, current_tenant_id, isolation_enabled

            if isolation_enabled():
                tid = current_tenant_id()
                filtered: list[ContactRecord] = []
                for c in rows:
                    if c.tenant_id is None or c.tenant_id == tid:
                        filtered.append(c)
                rows = filtered
        except Exception:
            pass
        if query:
            q = query.lower()
            rows = [
                c
                for c in rows
                if q in c.display_name.lower()
                or (c.organisation or "").lower().find(q) >= 0
                or any(q in (e.get("address", "")).lower() for e in c.emails)
            ]
        rows.sort(key=lambda c: (c.family_name or "", c.given_name or "", c.display_name))
        return rows[offset : offset + limit]

    async def get(self, contact_id: str, *, user_id: str | None = None) -> ContactRecord | None:
        from keprix.db.contacts_repo import _use_db, pg_get_contact

        if _use_db():
            pg_row = await pg_get_contact(contact_id, user_id)
            return ContactRecord.from_dict(pg_row) if pg_row else None
        record = self._contacts.get(contact_id)
        if record is None:
            return None
        if user_id is not None and record.user_id != user_id:
            return None
        try:
            from keprix.tenancy.isolation import TenantIsolationError, assert_tenant_owns

            assert_tenant_owns(record)
        except TenantIsolationError:
            return None
        return record

    async def update(
        self, contact_id: str, updates: dict[str, Any], *, user_id: str = "local"
    ) -> ContactRecord | None:
        from keprix.db.contacts_repo import _use_db, pg_update_contact

        if _use_db():
            pg_row = await pg_update_contact(contact_id, user_id, updates)
            return ContactRecord.from_dict(pg_row) if pg_row else None

        async with self._lock:
            record = self._contacts.get(contact_id)
            if record is None or record.user_id != user_id:
                return None
            if record.source != "manual":
                return None
            for key, value in updates.items():
                if value is not None and hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = _utcnow()
            return record

    async def delete(self, contact_id: str, *, user_id: str = "local") -> bool:
        from keprix.db.contacts_repo import _use_db, pg_delete_contact

        if _use_db():
            return bool(await pg_delete_contact(contact_id, user_id))

        async with self._lock:
            record = self._contacts.get(contact_id)
            if record is None or record.user_id != user_id:
                return False
            if record.source != "manual":
                return False
            del self._contacts[contact_id]
            return True

    async def find_by_email(self, address: str, *, user_id: str = "local") -> ContactRecord | None:
        from keprix.db.contacts_repo import _use_db, pg_find_by_email

        if _use_db():
            pg_row = await pg_find_by_email(user_id, address)
            return ContactRecord.from_dict(pg_row) if pg_row else None

        needle = address.lower().strip()
        for contact in self._contacts.values():
            if contact.user_id != user_id:
                continue
            for email in contact.emails:
                if (email.get("address") or "").lower() == needle:
                    return contact
        return None

    async def upsert_import(
        self,
        data: dict[str, Any],
        *,
        source: str,
        match_email: str | None = None,
        user_id: str = "local",
    ) -> tuple[ContactRecord, str]:
        from keprix.db.contacts_repo import _use_db, pg_upsert_import

        if _use_db():
            pg_result = await pg_upsert_import(
                user_id, data, source=source, match_email=match_email
            )
            if pg_result is None:
                raise RuntimeError("Failed to upsert contact")
            row, action = pg_result
            return ContactRecord.from_dict(row), action

        existing = None
        source_id = data.get("source_id")
        if source_id:
            for contact in self._contacts.values():
                if (
                    contact.user_id == user_id
                    and contact.source == source
                    and contact.source_id == source_id
                ):
                    existing = contact
                    break
        if existing is None and match_email:
            existing = await self.find_by_email(match_email, user_id=user_id)
        if existing:
            async with self._lock:
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
                        setattr(existing, key, data[key])
                existing.source = source
                existing.last_synced_at = _utcnow()
                existing.updated_at = _utcnow()
            return existing, "updated"
        created = await self.create(data, source=source, user_id=user_id)
        return created, "added"

    async def all_contacts(self, *, user_id: str | None = None) -> list[ContactRecord]:
        from keprix.db.contacts_repo import _use_db, pg_all_contacts

        if _use_db():
            pg_rows = await pg_all_contacts(user_id) or []
            return [ContactRecord.from_dict(r) for r in pg_rows]
        if user_id is None:
            return list(self._contacts.values())
        return [c for c in self._contacts.values() if c.user_id == user_id]

    async def get_preferences(self, user_id: str) -> ContactPreferencesRecord:
        from keprix.db.contacts_repo import _use_db, pg_get_preferences

        if _use_db():
            pg_row = await pg_get_preferences(user_id)
            if pg_row is None:
                return ContactPreferencesRecord(user_id=user_id)
            return ContactPreferencesRecord(
                user_id=pg_row["user_id"],
                confirm_before_email=pg_row["confirm_before_email"],
                confirm_before_call=pg_row["confirm_before_call"],
                read_back_draft=pg_row["read_back_draft"],
                updated_at=pg_row.get("updated_at") or _utcnow(),
            )
        if user_id not in self._preferences:
            self._preferences[user_id] = ContactPreferencesRecord(user_id=user_id)
        return self._preferences[user_id]

    async def update_preferences(
        self, user_id: str, updates: dict[str, Any]
    ) -> ContactPreferencesRecord:
        from keprix.db.contacts_repo import _use_db, pg_update_preferences

        if _use_db():
            pg_row = await pg_update_preferences(user_id, updates)
            if pg_row is None:
                return ContactPreferencesRecord(user_id=user_id)
            return ContactPreferencesRecord(
                user_id=pg_row["user_id"],
                confirm_before_email=pg_row["confirm_before_email"],
                confirm_before_call=pg_row["confirm_before_call"],
                read_back_draft=pg_row["read_back_draft"],
                updated_at=pg_row.get("updated_at") or _utcnow(),
            )
        prefs = await self.get_preferences(user_id)
        async with self._lock:
            for key, value in updates.items():
                if value is not None and hasattr(prefs, key):
                    setattr(prefs, key, value)
            prefs.updated_at = _utcnow()
            self._preferences[user_id] = prefs
        return prefs


_store: ContactStore | None = None


def get_contact_store() -> ContactStore:
    global _store
    if _store is None:
        _store = ContactStore()
    return _store


def reset_contact_store() -> None:
    global _store
    _store = ContactStore()

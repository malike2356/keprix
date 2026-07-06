"""In-memory contact store."""

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
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
        }


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

    async def create(self, data: dict[str, Any], *, source: str = "manual") -> ContactRecord:
        now = _utcnow()
        contact_id = str(uuid.uuid4())
        record = ContactRecord(
            id=contact_id,
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
        )
        async with self._lock:
            self._contacts[contact_id] = record
        return record

    async def list_contacts(
        self, *, query: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[ContactRecord]:
        rows = list(self._contacts.values())
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

    async def get(self, contact_id: str) -> ContactRecord | None:
        return self._contacts.get(contact_id)

    async def update(self, contact_id: str, updates: dict[str, Any]) -> ContactRecord | None:
        async with self._lock:
            record = self._contacts.get(contact_id)
            if record is None:
                return None
            if record.source != "manual":
                return None
            for key, value in updates.items():
                if value is not None and hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = _utcnow()
            return record

    async def delete(self, contact_id: str) -> bool:
        async with self._lock:
            record = self._contacts.get(contact_id)
            if record is None:
                return False
            if record.source != "manual":
                return False
            del self._contacts[contact_id]
            return True

    async def find_by_email(self, address: str) -> ContactRecord | None:
        needle = address.lower().strip()
        for contact in self._contacts.values():
            for email in contact.emails:
                if (email.get("address") or "").lower() == needle:
                    return contact
        return None

    async def upsert_import(
        self, data: dict[str, Any], *, source: str, match_email: str | None = None
    ) -> tuple[ContactRecord, str]:
        existing = None
        source_id = data.get("source_id")
        if source_id:
            for contact in self._contacts.values():
                if contact.source == source and contact.source_id == source_id:
                    existing = contact
                    break
        if existing is None and match_email:
            existing = await self.find_by_email(match_email)
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
                existing.updated_at = _utcnow()
            return existing, "updated"
        created = await self.create(data, source=source)
        return created, "added"

    async def all_contacts(self) -> list[ContactRecord]:
        return list(self._contacts.values())

    async def get_preferences(self, user_id: str) -> ContactPreferencesRecord:
        if user_id not in self._preferences:
            self._preferences[user_id] = ContactPreferencesRecord(user_id=user_id)
        return self._preferences[user_id]

    async def update_preferences(
        self, user_id: str, updates: dict[str, Any]
    ) -> ContactPreferencesRecord:
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

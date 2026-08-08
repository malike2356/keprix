"""Contacts HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from keprix.auth.dependencies import get_current_user
from keprix.contacts.enrichment import merge_enrichment, set_enrichment
from keprix.contacts.import_csv import import_csv_bytes
from keprix.contacts.import_vcf import import_vcf_bytes
from keprix.contacts.schemas import (
    ContactCreate,
    ContactEnrichmentUpdate,
    ContactOut,
    ContactPreferencesOut,
    ContactPreferencesUpdate,
    ContactUpdate,
    ImportSummary,
)
from keprix.contacts.search import contact_search
from keprix.contacts.store import get_contact_store

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


def _uid(user: dict) -> str:
    return str(user.get("id") or user.get("username") or "local")


def _out(user_id: str, record: Any) -> dict[str, Any]:
    return merge_enrichment(user_id, record.to_dict() if hasattr(record, "to_dict") else dict(record))


def _apply_enrichment(user_id: str, contact_id: str, body: dict[str, Any]) -> None:
    patch = {k: body.get(k) for k in ("tags", "whatsapp", "telegram", "role") if k in body}
    if patch:
        set_enrichment(user_id, contact_id, patch)


async def _contact_activity(user_id: str, contact: dict[str, Any]) -> dict[str, Any]:
    """Best-effort email/calendar activity matched by contact emails/name."""
    items: list[dict[str, Any]] = []
    emails = [
        str(e.get("address") or "").strip().lower()
        for e in (contact.get("emails") or [])
        if isinstance(e, dict) and e.get("address")
    ]
    name = str(contact.get("display_name") or "").strip().lower()

    try:
        from keprix.db.contacts_repo import _use_db
        from keprix.database import get_session_factory
        from keprix.db.models import EmailRow
        from sqlalchemy import or_, select

        if _use_db() and emails:
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    clauses = [EmailRow.from_address.ilike(f"%{addr}%") for addr in emails[:5]]
                    if name:
                        clauses.append(EmailRow.from_name.ilike(f"%{name}%"))
                    stmt = (
                        select(EmailRow)
                        .where(EmailRow.user_id == user_id)
                        .where(or_(*clauses))
                        .order_by(EmailRow.received_at.desc())
                        .limit(25)
                    )
                    rows = (await session.execute(stmt)).scalars().all()
                    for row in rows:
                        items.append(
                            {
                                "id": row.id,
                                "kind": "email",
                                "at": row.received_at.isoformat() if row.received_at else None,
                                "title": row.subject or "(no subject)",
                                "subtitle": row.from_address or "",
                                "href": f"/email?message={row.id}",
                                "meta": (row.preview or "")[:120],
                            }
                        )
    except Exception:
        pass

    try:
        from keprix.calendar.store import get_calendar_store  # type: ignore

        store = get_calendar_store()
        events = await store.list_events(user_id=user_id, limit=50)  # type: ignore[attr-defined]
        for event in events or []:
            title = str(event.get("title") or event.get("summary") or "")
            attendees = " ".join(str(a) for a in (event.get("attendees") or [])).lower()
            hay = f"{title} {attendees}".lower()
            if any(addr in hay for addr in emails) or (name and name in hay):
                items.append(
                    {
                        "id": str(event.get("id")),
                        "kind": "meeting",
                        "at": event.get("starts_at") or event.get("start"),
                        "title": title or "Meeting",
                        "subtitle": event.get("location") or "",
                        "href": f"/calendar?event={event.get('id')}",
                    }
                )
    except Exception:
        pass

    items.sort(key=lambda x: str(x.get("at") or ""), reverse=True)
    email_count = sum(1 for i in items if i.get("kind") == "email")
    meeting_count = sum(1 for i in items if i.get("kind") == "meeting")
    return {
        "items": items[:40],
        "counts": {"email": email_count, "meeting": meeting_count, "total": len(items)},
    }


@router.get("", response_model=list[ContactOut])
async def list_contacts(
    user: dict = Depends(get_current_user),
    q: str | None = None,
    source: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    uid = _uid(user)
    store = get_contact_store()
    rows = await store.list_contacts(user_id=uid, query=q, limit=limit, offset=offset)
    out = [_out(uid, r) for r in rows]
    if source and source != "all":
        src = source.strip().lower()
        out = [c for c in out if str(c.get("source") or "").lower() == src]
    return out


@router.get("/search")
async def search_contacts(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await contact_search(q, limit=limit, user_id=_uid(user))


@router.get("/preferences", response_model=ContactPreferencesOut)
async def get_preferences(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = get_contact_store()
    prefs = await store.get_preferences(_uid(user))
    return prefs.to_dict()


@router.put("/preferences", response_model=ContactPreferencesOut)
async def update_preferences(
    body: ContactPreferencesUpdate, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    store = get_contact_store()
    prefs = await store.update_preferences(_uid(user), body.model_dump(exclude_unset=True))
    return prefs.to_dict()


@router.post("/import/vcf", response_model=ImportSummary)
async def import_vcf(
    file: UploadFile = File(...), user: dict = Depends(get_current_user)
) -> dict[str, int]:
    content = await file.read()
    return await import_vcf_bytes(content, user_id=_uid(user))


@router.post("/import/csv", response_model=ImportSummary)
async def import_csv(
    file: UploadFile = File(...), user: dict = Depends(get_current_user)
) -> dict[str, int]:
    content = await file.read()
    return await import_csv_bytes(content, user_id=_uid(user))


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(contact_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    store = get_contact_store()
    record = await store.get(contact_id, user_id=uid)
    if record is None:
        raise HTTPException(404, "Contact not found")
    return _out(uid, record)


@router.get("/{contact_id}/activity")
async def get_contact_activity(contact_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    store = get_contact_store()
    record = await store.get(contact_id, user_id=uid)
    if record is None:
        raise HTTPException(404, "Contact not found")
    return await _contact_activity(uid, _out(uid, record))


@router.patch("/{contact_id}/enrichment", response_model=ContactOut)
async def patch_enrichment(
    contact_id: str,
    body: ContactEnrichmentUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    uid = _uid(user)
    store = get_contact_store()
    record = await store.get(contact_id, user_id=uid)
    if record is None:
        raise HTTPException(404, "Contact not found")
    set_enrichment(uid, contact_id, body.model_dump(exclude_unset=True))
    return _out(uid, record)


@router.post("", status_code=201, response_model=ContactOut)
async def create_contact(
    body: ContactCreate, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    uid = _uid(user)
    store = get_contact_store()
    data = body.model_dump()
    enrichment = {
        "tags": data.pop("tags", []) or [],
        "whatsapp": data.pop("whatsapp", None),
        "telegram": data.pop("telegram", None),
        "role": data.pop("role", None),
    }
    data["emails"] = [e.model_dump() for e in body.emails]
    data["phones"] = [p.model_dump() for p in body.phones]
    data["addresses"] = [a.model_dump() for a in body.addresses]
    record = await store.create(data, source="manual", user_id=uid)
    _apply_enrichment(uid, record.id, enrichment)
    return _out(uid, record)


@router.put("/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: str, body: ContactUpdate, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    store = get_contact_store()
    uid = _uid(user)
    updates = body.model_dump(exclude_unset=True)
    enrichment = {}
    for key in ("tags", "whatsapp", "telegram", "role"):
        if key in updates:
            enrichment[key] = updates.pop(key)
    if "emails" in updates and updates["emails"] is not None:
        updates["emails"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in updates["emails"]]
    if "phones" in updates and updates["phones"] is not None:
        updates["phones"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in updates["phones"]]
    if "addresses" in updates and updates["addresses"] is not None:
        updates["addresses"] = [
            a.model_dump() if hasattr(a, "model_dump") else a for a in updates["addresses"]
        ]

    record = None
    if updates:
        record = await store.update(contact_id, updates, user_id=uid)
        if record is None:
            existing = await store.get(contact_id, user_id=uid)
            if existing is None:
                raise HTTPException(404, "Contact not found")
            if existing.source != "manual" and updates:
                # Allow enrichment-only updates for synced contacts
                if not enrichment:
                    raise HTTPException(400, "Synced contacts must be edited at the source")
            record = existing
    else:
        record = await store.get(contact_id, user_id=uid)
        if record is None:
            raise HTTPException(404, "Contact not found")

    if enrichment:
        _apply_enrichment(uid, contact_id, enrichment)
    return _out(uid, record)


@router.delete("/{contact_id}", status_code=200)
async def delete_contact(contact_id: str, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    store = get_contact_store()
    uid = _uid(user)
    existing = await store.get(contact_id, user_id=uid)
    if existing is None:
        raise HTTPException(404, "Contact not found")
    if not await store.delete(contact_id, user_id=uid):
        raise HTTPException(400, "Synced contacts cannot be deleted in keprix")
    return {"ok": True}

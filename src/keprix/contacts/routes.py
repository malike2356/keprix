"""Contacts HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from keprix.auth.dependencies import get_current_user
from keprix.contacts.import_csv import import_csv_bytes
from keprix.contacts.import_vcf import import_vcf_bytes
from keprix.contacts.schemas import (
    ContactCreate,
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


@router.get("", response_model=list[ContactOut])
async def list_contacts(
    user: dict = Depends(get_current_user),
    q: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    store = get_contact_store()
    rows = await store.list_contacts(user_id=_uid(user), query=q, limit=limit, offset=offset)
    return [r.to_dict() for r in rows]


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
    store = get_contact_store()
    record = await store.get(contact_id, user_id=_uid(user))
    if record is None:
        raise HTTPException(404, "Contact not found")
    return record.to_dict()


@router.post("", status_code=201, response_model=ContactOut)
async def create_contact(
    body: ContactCreate, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    store = get_contact_store()
    data = body.model_dump()
    data["emails"] = [e.model_dump() for e in body.emails]
    data["phones"] = [p.model_dump() for p in body.phones]
    data["addresses"] = [a.model_dump() for a in body.addresses]
    record = await store.create(data, source="manual", user_id=_uid(user))
    return record.to_dict()


@router.put("/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: str, body: ContactUpdate, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    store = get_contact_store()
    uid = _uid(user)
    updates = body.model_dump(exclude_unset=True)
    if "emails" in updates and updates["emails"] is not None:
        updates["emails"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in updates["emails"]]
    if "phones" in updates and updates["phones"] is not None:
        updates["phones"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in updates["phones"]]
    if "addresses" in updates and updates["addresses"] is not None:
        updates["addresses"] = [
            a.model_dump() if hasattr(a, "model_dump") else a for a in updates["addresses"]
        ]
    record = await store.update(contact_id, updates, user_id=uid)
    if record is None:
        existing = await store.get(contact_id, user_id=uid)
        if existing is None:
            raise HTTPException(404, "Contact not found")
        raise HTTPException(400, "Synced contacts must be edited at the source")
    return record.to_dict()


@router.delete("/{contact_id}", status_code=200)
async def delete_contact(contact_id: str, user: dict = Depends(get_current_user)) -> None:
    store = get_contact_store()
    uid = _uid(user)
    existing = await store.get(contact_id, user_id=uid)
    if existing is None:
        raise HTTPException(404, "Contact not found")
    if not await store.delete(contact_id, user_id=uid):
        raise HTTPException(400, "Synced contacts cannot be deleted in keprix")

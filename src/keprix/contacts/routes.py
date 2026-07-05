"""Contacts HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile

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


def _user_id(request: Request) -> str:
    return request.headers.get("x-user-id", "").strip() or "local"


@router.get("", response_model=list[ContactOut])
async def list_contacts(
    request: Request,
    q: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    store = get_contact_store()
    rows = await store.list_contacts(query=q, limit=limit, offset=offset)
    return [r.to_dict() for r in rows]


@router.get("/search")
async def search_contacts(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
) -> list[dict[str, Any]]:
    return await contact_search(q, limit=limit)


@router.get("/preferences", response_model=ContactPreferencesOut)
async def get_preferences(request: Request) -> dict[str, Any]:
    store = get_contact_store()
    prefs = await store.get_preferences(_user_id(request))
    return prefs.to_dict()


@router.put("/preferences", response_model=ContactPreferencesOut)
async def update_preferences(
    body: ContactPreferencesUpdate, request: Request
) -> dict[str, Any]:
    store = get_contact_store()
    prefs = await store.update_preferences(
        _user_id(request), body.model_dump(exclude_unset=True)
    )
    return prefs.to_dict()


@router.post("/import/vcf", response_model=ImportSummary)
async def import_vcf(file: UploadFile = File(...)) -> dict[str, int]:
    content = await file.read()
    return await import_vcf_bytes(content)


@router.post("/import/csv", response_model=ImportSummary)
async def import_csv(file: UploadFile = File(...)) -> dict[str, int]:
    content = await file.read()
    return await import_csv_bytes(content)


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(contact_id: str) -> dict[str, Any]:
    store = get_contact_store()
    record = await store.get(contact_id)
    if record is None:
        raise HTTPException(404, "Contact not found")
    return record.to_dict()


@router.post("", status_code=201, response_model=ContactOut)
async def create_contact(body: ContactCreate) -> dict[str, Any]:
    store = get_contact_store()
    data = body.model_dump()
    data["emails"] = [e.model_dump() for e in body.emails]
    data["phones"] = [p.model_dump() for p in body.phones]
    data["addresses"] = [a.model_dump() for a in body.addresses]
    record = await store.create(data, source="manual")
    return record.to_dict()


@router.put("/{contact_id}", response_model=ContactOut)
async def update_contact(contact_id: str, body: ContactUpdate) -> dict[str, Any]:
    store = get_contact_store()
    updates = body.model_dump(exclude_unset=True)
    if "emails" in updates and updates["emails"] is not None:
        updates["emails"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in updates["emails"]]
    if "phones" in updates and updates["phones"] is not None:
        updates["phones"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in updates["phones"]]
    if "addresses" in updates and updates["addresses"] is not None:
        updates["addresses"] = [
            a.model_dump() if hasattr(a, "model_dump") else a for a in updates["addresses"]
        ]
    record = await store.update(contact_id, updates)
    if record is None:
        existing = await store.get(contact_id)
        if existing is None:
            raise HTTPException(404, "Contact not found")
        raise HTTPException(400, "Synced contacts must be edited at the source")
    return record.to_dict()


@router.delete("/{contact_id}", status_code=200)
async def delete_contact(contact_id: str) -> None:
    store = get_contact_store()
    existing = await store.get(contact_id)
    if existing is None:
        raise HTTPException(404, "Contact not found")
    if not await store.delete(contact_id):
        raise HTTPException(400, "Synced contacts cannot be deleted in keprix")

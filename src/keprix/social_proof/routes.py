"""HTTP routes for social proof curation and public listing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.social_proof import (
    approve,
    assign_product,
    collect_primary,
    get_store,
    reject,
    run_weekly,
    tag,
)

router = APIRouter(prefix="/api/social-proof", tags=["social-proof"])
LOCAL_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample-collect.json"
FIXTURES = LOCAL_FIXTURES


class ManualBody(BaseModel):
    text: str = Field(min_length=1)
    author: str = Field(min_length=1)
    link: str = Field(min_length=8)
    platform: str = "manual"
    product: str = "keprix"
    tags: list[str] = Field(default_factory=list)


class TagBody(BaseModel):
    tags: list[str] = Field(default_factory=list)


class AssignBody(BaseModel):
    product: str = Field(min_length=1)


def _fixtures_path(use_fixtures: bool) -> str | None:
    if not use_fixtures:
        return None
    if LOCAL_FIXTURES.exists():
        return str(LOCAL_FIXTURES)
    if FIXTURES.exists():
        return str(FIXTURES)
    return None


@router.get("/public")
async def public_approved(product: str | None = None, tag_name: str | None = None) -> dict[str, Any]:
    store = get_store()
    rows = store.list(status="approved", product=product, tag=tag_name)
    return {"ok": True, "testimonials": rows}


@router.get("")
async def list_all(
    status: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    store = get_store()
    rows = store.list(status=status) if status else store.list()
    return {"ok": True, "count": len(rows), "testimonials": rows}


@router.post("/collect")
async def collect_now(
    fixtures: bool = False,
    weekly: bool = False,
    force: bool = False,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    store = get_store()
    path = _fixtures_path(fixtures or os_environ_fixtures())
    if weekly:
        return {"ok": True, **run_weekly(store, fixtures_path=path, force=force, product="keprix")}
    results = collect_primary(store, fixtures_path=path, product="keprix")
    return {"ok": True, "results": results}


def os_environ_fixtures() -> bool:
    import os

    return os.environ.get("KEPRIX_SOCIAL_PROOF_USE_FIXTURES") == "1"


@router.post("/manual")
async def add_manual(body: ManualBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    store = get_store()
    item, _dup = store.upsert(
        {
            "text": body.text,
            "author": body.author,
            "url": body.link,
            "platform": body.platform,
            "product": body.product,
            "tags": body.tags,
            "status": "pending",
        }
    )
    return {"ok": True, "testimonial": item}


@router.post("/{item_id}/approve")
async def approve_item(item_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = approve(get_store(), item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "testimonial": row}


@router.post("/{item_id}/reject")
async def reject_item(item_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = reject(get_store(), item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "testimonial": row}


@router.post("/{item_id}/tag")
async def tag_item(item_id: str, body: TagBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = tag(get_store(), item_id, body.tags)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "testimonial": row}


@router.post("/{item_id}/assign")
async def assign_item(item_id: str, body: AssignBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = assign_product(get_store(), item_id, body.product)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "testimonial": row}

"""Tool adapter HTTP routes (Prompt 56)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.backend.tools.adapters.registry import get_adapter, list_adapters, list_categories, run_adapter

router = APIRouter(prefix="/api/tools/adapters", tags=["tool-adapters"])


class AdapterRunBody(BaseModel):
    action: str = "search"
    params: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True
    approved: bool = False


@router.get("")
async def adapters_index(category: str | None = None, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"categories": list_categories(), "adapters": list_adapters(category=category)}


@router.get("/{name}")
async def adapter_detail(name: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    adapter = get_adapter(name)
    if adapter is None:
        raise HTTPException(status_code=404, detail="Adapter not found")
    return adapter.metadata()


@router.post("/{name}/run")
async def adapter_run(name: str, body: AdapterRunBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    result = await run_adapter(
        name,
        body.action,
        body.params,
        dry_run=body.dry_run,
        approved=body.approved,
    )
    return result.to_dict()

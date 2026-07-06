"""Generated tool HTTP routes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.agent.keprix.installer import LiveInstaller
from keprix.agent.keprix.mutation import get_mutation_engine
from keprix.agent.keprix.store import get_generated_tool_store
from keprix.keys.local_access import effective_access_level
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/agent/tools/generated", tags=["mutation"])


class ApproveBody(BaseModel):
    channel: str = "web_ui"


class RejectBody(BaseModel):
    reason: str | None = None
    channel: str = "web_ui"


class RunCycleBody(BaseModel):
    task: str
    available_tools: list[str] = Field(default_factory=list)


def _require_admin() -> str:
    if effective_access_level() in {"developer", "admin", "owner"}:
        return "admin"
    raise HTTPException(status_code=403, detail="Admin access required")


@router.get("")
async def list_generated(_session: str = Depends(require_developer_session)) -> dict[str, Any]:
    records = get_generated_tool_store().list_all()
    return {"tools": [asdict(record) for record in records]}


@router.get("/pending")
async def list_pending(_session: str = Depends(require_developer_session)) -> dict[str, Any]:
    records = get_mutation_engine().list_pending()
    return {"tools": [asdict(record) for record in records]}


@router.get("/{record_id}")
async def get_generated(record_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    record = get_generated_tool_store().get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Generated tool not found")
    return asdict(record)


@router.post("/{record_id}/approve")
async def approve_generated(
    record_id: str,
    channel: str = Query(default="web_ui"),
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    result = await get_mutation_engine().approve(record_id, approver_id="admin", channel=channel)
    if result is None:
        raise HTTPException(status_code=404, detail="Pending tool not found")
    record = result.record
    return {
        **asdict(record),
        "record": asdict(record),
        "retry_message": result.retry_message,
    }


@router.post("/{record_id}/reject")
async def reject_generated(
    record_id: str,
    body: RejectBody,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    record = await get_mutation_engine().reject(
        record_id,
        approver_id="admin",
        reason=body.reason,
        channel=body.channel,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Pending tool not found")
    return asdict(record)


@router.delete("/{record_id}")
async def delete_generated_files(record_id: str, _admin: str = Depends(_require_admin)) -> dict[str, Any]:
    record = get_generated_tool_store().get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Generated tool not found")
    removed = LiveInstaller().remove_from_filesystem(record)
    return {"removed": removed, "record_id": record_id}


@router.post("/cycle")
async def run_mutation_cycle(body: RunCycleBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    return await get_mutation_engine().run_cycle(body.task, body.available_tools)

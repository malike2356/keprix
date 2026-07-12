"""Agent OS run ledger and loop profile routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.loop_profile_engine import LoopProfileEngine
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.run_ledger_store import RunLedgerStore
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user
from keprix.integrations.scout_lifecycle_client import emit_scout_lifecycle_event

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class BaselineBody(BaseModel):
    entry_ids: list[str] | None = None
    last_n: int = Field(default=5, ge=1, le=50)


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


def _split_source(source: str) -> tuple[str, str]:
    if ":" not in source:
        raise HTTPException(status_code=400, detail="source must be '<source_type>:<source_id>'")
    source_type, source_id = source.split(":", 1)
    if not source_type or not source_id:
        raise HTTPException(status_code=400, detail="source must include type and id")
    return source_type, source_id


@router.get("/ledger")
async def list_ledger(
    source_type: str | None = None,
    source_id: str | None = None,
    workspace_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    entries = RunLedgerStore().list(
        source_type=source_type,
        source_id=source_id,
        workspace_id=workspace_id,
        status=status,
        limit=limit,
    )
    return {"entries": [entry.to_dict() for entry in entries], "count": len(entries)}


@router.get("/ledger/{entry_id}")
async def get_ledger_entry(entry_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    entry = RunLedgerStore().get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    return entry.to_dict()


@router.post("/loop-profiles/{source}/baseline")
async def set_loop_baseline(source: str, body: BaselineBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    source_type, source_id = _split_source(source)
    profile = LoopProfileEngine().record_baseline(source_type, source_id, body.entry_ids, last_n=body.last_n)
    record_onboarding_event_for_user(user, "loop_profile.baseline_set")
    return profile.to_dict()


@router.get("/loop-profiles/{source}/proposals")
async def get_loop_proposals(source: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    source_type, source_id = _split_source(source)
    proposals = LoopProfileEngine().analyze_drift(source_type, source_id)
    if proposals:
        await emit_scout_lifecycle_event(
            "loop.proposal.created",
            {"source_type": source_type, "source_id": source_id, "proposal_count": len(proposals)},
            workspace_id="default",
        )
    return {"proposals": proposals, "count": len(proposals)}


@router.post("/loop-profiles/proposals/{proposal_id}/apply")
async def apply_loop_proposal(proposal_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    result = LoopProfileEngine().apply_proposal(proposal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Loop proposal not found")
    return result

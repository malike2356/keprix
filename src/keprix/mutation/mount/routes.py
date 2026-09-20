"""REST routes for mutation mount proposals."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.keys.local_access import effective_access_level
from keprix.mutation.mount import (
    MountApprovalError,
    MountBanError,
    MountIntent,
    banned_summary,
    get_mutation_mount_service,
)
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/mutation/mounts", tags=["mutation-mounts"])


class ProposeBody(BaseModel):
    action: str
    target_id: str
    seam: str | None = None
    provider_id: str | None = None
    declared_tools: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    proposed_by: str = "agent"
    workspace_id: str = "default"
    trajectory_id: str | None = None


class DecideBody(BaseModel):
    actor: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(default="", max_length=2000)
    allow_same_actor: bool = False


def _require_admin() -> str:
    if effective_access_level() in {"developer", "admin", "owner"}:
        return "admin"
    raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/bans")
async def get_mount_bans(
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    return banned_summary()


@router.get("")
async def list_mount_proposals(
    status: str | None = None,
    workspace_id: str = "default",
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    svc = get_mutation_mount_service()
    items = svc.store.list(workspace_id=workspace_id, status=status)
    return {"items": [i.to_dict() for i in items], "total": len(items)}


@router.post("")
async def propose_mount(
    body: ProposeBody,
    _admin: str = Depends(_require_admin),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    svc = get_mutation_mount_service()
    try:
        intent = MountIntent(
            action=body.action,  # type: ignore[arg-type]
            target_id=body.target_id,
            seam=body.seam,
            provider_id=body.provider_id,
            declared_tools=body.declared_tools,
            metadata=body.metadata,
        )
        proposal = svc.propose(
            intent,
            proposed_by=body.proposed_by,
            workspace_id=body.workspace_id,
            trajectory_id=body.trajectory_id,
        )
    except (MountBanError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.get("/{proposal_id}")
async def get_mount_proposal(
    proposal_id: str,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    svc = get_mutation_mount_service()
    proposal = svc.store.get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    return proposal.to_dict()


@router.post("/{proposal_id}/approve")
async def approve_mount(
    proposal_id: str,
    body: DecideBody,
    _admin: str = Depends(_require_admin),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    svc = get_mutation_mount_service()
    try:
        proposal = svc.approve(
            proposal_id,
            approved_by=body.actor,
            allow_same_actor=body.allow_same_actor,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MountApprovalError, MountBanError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.post("/{proposal_id}/deny")
async def deny_mount(
    proposal_id: str,
    body: DecideBody,
    _admin: str = Depends(_require_admin),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    svc = get_mutation_mount_service()
    try:
        proposal = svc.deny(proposal_id, denied_by=body.actor, reason=body.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MountApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.post("/{proposal_id}/reverse")
async def reverse_mount(
    proposal_id: str,
    body: DecideBody,
    _admin: str = Depends(_require_admin),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    svc = get_mutation_mount_service()
    try:
        proposal = svc.reverse(proposal_id, who=body.actor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MountApprovalError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()

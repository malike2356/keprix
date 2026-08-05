"""Enterprise connector governance queue."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix.licensing.dependencies import enterprise_feature

router = APIRouter(prefix="/api/integrations/governance", tags=["integrations-governance"])

_PENDING: dict[str, dict[str, Any]] = {}


class GovernanceRequest(BaseModel):
    connector_id: str
    requested_by: str = "local"


class GovernanceApprove(BaseModel):
    request_id: str
    approved_by: str = "admin"


@router.post("/request")
async def request_connector_install(body: GovernanceRequest) -> dict[str, Any]:
    request_id = f"cg_{uuid4().hex}"
    row = {
        "id": request_id,
        "connector_id": body.connector_id,
        "requested_by": body.requested_by,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _PENDING[request_id] = row
    return {"request": row}


@router.get("/pending")
async def pending_connector_installs(
    _feature: None = Depends(enterprise_feature("connector_governance")),
) -> dict[str, Any]:
    return {"requests": [row for row in _PENDING.values() if row["status"] == "pending"]}


@router.post("/approve")
async def approve_connector_install(
    body: GovernanceApprove,
    _feature: None = Depends(enterprise_feature("connector_governance")),
) -> dict[str, Any]:
    row = _PENDING.get(body.request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Connector governance request not found")
    row["status"] = "approved"
    row["approved_by"] = body.approved_by
    row["approved_at"] = datetime.now(timezone.utc).isoformat()
    return {"request": row}

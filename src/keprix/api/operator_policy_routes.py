"""Admin operator policy API (Prompt 297).

GET  /api/admin/policy
PUT  /api/admin/policy  { "profile": "permissive", "product_id": "...", "workspace_id": "..." }
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin

router = APIRouter(prefix="/api/admin/policy", tags=["admin"])


class PolicyPutBody(BaseModel):
    profile: str = Field(..., description="strict | standard | permissive")
    product_id: Optional[str] = None
    workspace_id: Optional[str] = "default"


@router.get("")
@router.get("/")
async def get_policy(
    product_id: Optional[str] = None,
    workspace_id: Optional[str] = "default",
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    from keprix.security.operator_policy import get_operator_policy, profile_knob_diff

    policy = get_operator_policy(product_id=product_id, workspace_id=workspace_id or "default")
    return {
        "ok": True,
        "policy": policy.to_dict(),
        "knob_matrix": profile_knob_diff(),
        "empty_state": (
            None
            if policy.source != "default"
            else "Using default profile: standard"
        ),
    }


@router.put("")
@router.put("/")
async def put_policy(
    body: PolicyPutBody,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    from keprix.security.audit import audit_log
    from keprix.security.operator_policy import set_operator_policy

    updated_by = str(admin.get("id") or admin.get("email") or "admin")
    policy = set_operator_policy(
        body.profile,
        product_id=body.product_id,
        workspace_id=body.workspace_id or "default",
        updated_by=updated_by,
    )
    # Extra awaitable audit for API path (set_operator_policy also best-effort).
    await audit_log(
        "operator_policy.changed",
        user_id=updated_by,
        event_data=policy.to_dict(),
        severity="warning" if policy.profile.value == "permissive" else "info",
    )
    return {"ok": True, "policy": policy.to_dict()}

"""Social organic posting routes (prompt 07). Decision-gated."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm import social_posting as sp
from keprix.crm.roles import require_cap
from keprix.crm.routes import _workspace
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm/social-posting", tags=["crm-social-posting"])


class PublishBody(BaseModel):
    channel: str
    text: str
    media_url: str | None = None


@router.get("/scopes")
async def scopes(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    return {"ok": True, "scopes": sp.supported_scopes(), "decisions": sp.POSTING_DECISIONS}


@router.post("/publish")
async def publish(
    body: PublishBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="text is required")
    if body.channel not in sp.POSTING_DECISIONS:
        raise HTTPException(status_code=422, detail="unknown channel")
    store = get_crm_store()
    ws = _workspace(workspace_id, x_workspace_id, user)
    result = sp.publish(body.channel, body.text, body.media_url, workspace_id=ws)
    if result["status"] in {"published", "not_configured", "pending_approval", "unsupported"}:
        sp.record_publish_result(store, ws, body.channel, result)
    return result

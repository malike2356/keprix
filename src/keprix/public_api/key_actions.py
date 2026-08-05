"""Self-service API key controls (leak disable, etc.)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from keprix.public_api.auth import require_api_key
from keprix.public_api.keys import ApiKeyContext, get_api_key_store

router = APIRouter(tags=["openai-compat"])


@router.post("/v1/keys/self-disable")
async def self_disable_key(ctx: ApiKeyContext = Depends(require_api_key)) -> dict:
    """Disable the calling key when auto-disable-if-leaked is enabled.

    External scanners or the key owner can call this after a leak without
    needing a developer session.
    """
    if ctx.key_id == "env-token":
        raise HTTPException(status_code=400, detail="Environment break-glass token cannot self-disable")
    if not ctx.auto_disable_if_leaked:
        raise HTTPException(
            status_code=400,
            detail="Auto-disable if leaked is turned off for this key",
        )
    if not get_api_key_store().disable_if_leaked(ctx.key_id, reason="self_disable"):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"disabled": True, "id": ctx.key_id, "reason": "self_disable"}

"""Carina agent bridge -- POST /carina/agent/run

Compatibility shim for product-sidecar ``agent.run``
(``POST /v1/products/{carina|aiva}/invoke``). Existing shared-token clients
keep working until ``KEPRIX_DISABLE_SHARED_COMPAT_TOKEN=1``; prefer short-lived
audience-bound exchange tokens for new integrations.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from keprix.agent.carina_bridge import CarinaAgentBridge, CarinaToolNotRegistered
from keprix.product_sidecar.auth import (
    get_token_service,
    shared_bootstrap_token,
    shared_compat_enabled,
    shared_compat_token_usable,
)
from keprix.security.aiva_scout import get_aiva_scout_guard

router = APIRouter(prefix="/carina", tags=["carina-bridge"])
bridge = CarinaAgentBridge()

try:
    from keprix.aiva_analytics.routes import router as _aiva_analytics_router

    router.include_router(_aiva_analytics_router)
except Exception:
    pass


def _shared_token() -> str:
    return shared_bootstrap_token()


def require_carina_agent_auth(request: Request) -> dict[str, Any]:
    """Accept shared compat token (if enabled) or sidecar exchange bearer."""
    auth = request.headers.get("Authorization", "").strip()
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")
    token_raw = auth[7:].strip()
    usable = shared_compat_token_usable()
    if usable and token_raw == usable:
        return {"token_mode": "shared_compat"}

    raw_shared = shared_bootstrap_token()
    if not shared_compat_enabled() and raw_shared and token_raw == raw_shared:
        raise HTTPException(
            status_code=401,
            detail="Shared compat token disabled; use audience-bound exchange credentials",
        )

    # Exchange / session credential path
    try:
        ctx = get_token_service().authenticate_request(
            authorization=auth,
            product=str(request.headers.get("X-Keprix-Product") or "propreneur"),
            correlation_id=str(request.headers.get("X-Correlation-Id") or uuid.uuid4()),
            required_audience="keprix-product-sidecar",
        )
        return {"token_mode": ctx.token_mode, "workspace_id": ctx.workspace_id, "actor_id": ctx.actor_id}
    except ValueError:
        if not usable and not raw_shared:
            raise HTTPException(
                status_code=503,
                detail="CARINA_KEPRIX_SHARED_TOKEN is not configured and no exchange token presented",
            )
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


def require_carina_shared_token(request: Request) -> None:
    """Legacy helper used by older tests; prefers require_carina_agent_auth."""
    require_carina_agent_auth(request)


@router.post("/agent/run")
async def agent_run(request: Request) -> dict[str, Any]:
    """Execute an agent turn for a Carina/Aiva workspace."""
    auth_meta = require_carina_agent_auth(request)

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    workspace_id = str(body.get("workspace_id") or "").strip()
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")

    token_workspace = str(auth_meta.get("workspace_id") or "").strip()
    if token_workspace and token_workspace != workspace_id:
        raise HTTPException(status_code=403, detail="workspace_id does not match credential")

    system_prompt = body.get("system_prompt")
    if system_prompt is None:
        raise HTTPException(status_code=422, detail="system_prompt is required")

    messages = body.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=422, detail="messages must be an array")

    kill = get_aiva_scout_guard().check_kill(workspace_id)
    if kill.active:
        return {
            "message": {
                "role": "assistant",
                "content": "Agent execution suspended by Scout. Contact your administrator.",
            },
            "tool_calls": [],
            "finish_reason": "error",
            "session_id": str(body.get("session_id") or ""),
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": "scout_kill_switch",
            "scout": {
                "scope": kill.scope,
                "reason": kill.reason,
                "activated_by": kill.activated_by,
            },
        }

    correlation_id = str(
        request.headers.get("X-Correlation-Id")
        or body.get("correlation_id")
        or f"corr_{uuid.uuid4().hex[:12]}"
    )

    try:
        result = await bridge.run(
            workspace_id=workspace_id,
            session_id=body.get("session_id"),
            model=str(body.get("model") or "deepseek-v4-pro"),
            temperature=float(body.get("temperature", 0.7)),
            system_prompt=str(system_prompt),
            messages=messages,
            tools=body.get("tools") or [],
            carina_tools=body.get("carina_tools") or [],
            scout=get_aiva_scout_guard(),
            worker_id=(str(body.get("worker_id")).strip() if body.get("worker_id") else None),
            inject_worker_kb=body.get("inject_worker_kb", True) is not False,
            confidence=(
                float(body["confidence"])
                if body.get("confidence") is not None and str(body.get("confidence")).strip() != ""
                else None
            ),
            force_escalate=bool(body.get("force_escalate")),
            escalation_enabled=body.get("escalation_enabled", True) is not False,
            correlation_id=correlation_id,
            product=str(body.get("product") or "propreneur"),
        )
    except CarinaToolNotRegistered as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "tool_not_registered", "tool": exc.tool_name},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if isinstance(result, dict):
        result.setdefault("token_mode", auth_meta.get("token_mode"))
        result.setdefault("correlation_id", correlation_id)
    return result

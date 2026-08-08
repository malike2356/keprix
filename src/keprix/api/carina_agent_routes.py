"""Carina agent bridge -- POST /carina/agent/run

Compatibility shim for product-sidecar ``agent.run``
(``POST /v1/products/{carina|aiva}/invoke``). Existing shared-token clients
keep working; prefer the capabilities API for new integrations.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from keprix.agent.carina_bridge import CarinaAgentBridge, CarinaToolNotRegistered
from keprix.security.aiva_scout import get_aiva_scout_guard

router = APIRouter(prefix="/carina", tags=["carina-bridge"])
bridge = CarinaAgentBridge()

try:
    from keprix.aiva_analytics.routes import router as _aiva_analytics_router

    router.include_router(_aiva_analytics_router)
except Exception:
    pass


def _shared_token() -> str:
    return (
        os.environ.get("CARINA_KEPRIX_SHARED_TOKEN", "").strip()
        or os.environ.get("KEPRIX_CARINA_SHARED_TOKEN", "").strip()
    )


def require_carina_shared_token(request: Request) -> None:
    expected_token = _shared_token()
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="CARINA_KEPRIX_SHARED_TOKEN is not configured",
        )
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {expected_token}"
    if auth != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


@router.post("/agent/run")
async def agent_run(request: Request) -> dict[str, Any]:
    """Execute an agent turn for a Carina/Aiva workspace."""
    require_carina_shared_token(request)

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    workspace_id = str(body.get("workspace_id") or "").strip()
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")

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

    return result

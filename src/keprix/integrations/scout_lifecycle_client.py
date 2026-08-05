"""Scout lifecycle webhook client for playbook publish/run events."""

from __future__ import annotations

import logging
import os
from uuid import uuid4

_log = logging.getLogger(__name__)


async def emit_scout_lifecycle_event(
    event_type: str,
    payload: dict,
    *,
    workspace_id: str,
) -> str | None:
    """POST a lifecycle event to Scout when enabled; no-op otherwise."""
    if os.environ.get("LABYRINTH_ENABLED") not in {"1", "true", "TRUE", "yes"}:
        return None
    url = os.environ.get("LABYRINTH_SCOUT_WEBHOOK_URL") or os.environ.get("SCOUT_WEBHOOK_URL")
    if not url:
        return None
    event_id = f"evt_{uuid4().hex}"
    body = {
        "event_id": event_id,
        "event_type": event_type,
        "workspace_id": workspace_id,
        "payload": payload,
    }
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("LABYRINTH_SCOUT_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
    except Exception as exc:
        _log.warning("Scout lifecycle webhook failed: %s", exc)
        return event_id
    return event_id

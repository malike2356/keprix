"""Discovery state API for the home page discovery card system.

GET  /api/workspace/discovery-state  - Aggregated workspace signals for trigger evaluation
PATCH /api/workspace/discovery-state - Mark a trigger as acted_on or mark brain graph visited
"""

from __future__ import annotations

import time

from fastapi import APIRouter
from pydantic import BaseModel

from keprix.workspace.discovery_state import DiscoveryState, get_discovery_store

router = APIRouter(prefix="/api/workspace/discovery-state", tags=["workspace"])


class ActOnRequest(BaseModel):
    trigger_id: str
    action: str   # "acted_on" | "brain_graph_visited"


@router.get("")
async def get_discovery_state(workspace_id: str = "default") -> dict:
    """Return aggregated discovery signals. All counts only - no full objects.

    In production the counts come from fast DB queries or a pre-computed cache.
    Here we return defaults that the frontend can override via real endpoints.
    """
    store = get_discovery_store()
    brain_visited = await store.is_brain_graph_visited(workspace_id)
    acted_ids = await store.get_acted_on_ids(workspace_id)

    state = DiscoveryState(brain_graph_visited=brain_visited)
    result = state.to_dict()
    result["actedOnTriggerIds"] = list(acted_ids)
    return result


@router.patch("")
async def patch_discovery_state(body: ActOnRequest, workspace_id: str = "default") -> dict:
    """Mark a trigger as acted_on, or mark the brain graph as visited."""
    store = get_discovery_store()

    if body.action == "acted_on":
        await store.mark_acted_on(workspace_id, body.trigger_id, time.time())
        return {"ok": True, "trigger_id": body.trigger_id, "action": "acted_on"}

    if body.action == "brain_graph_visited":
        await store.mark_brain_graph_visited(workspace_id)
        return {"ok": True, "action": "brain_graph_visited"}

    return {"ok": False, "error": f"Unknown action: {body.action}"}

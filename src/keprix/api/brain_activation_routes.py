"""SSE routes for live brain graph activation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

from keprix.auth.dependencies import get_current_user
from keprix.brain.activation_bus import activation_bus

router = APIRouter(prefix="/api/brain/graph", tags=["brain-activation"])


async def _events(request: Request, workspace_id: str, session_id: str) -> AsyncIterator[bytes]:
    queue = activation_bus.subscribe(workspace_id)
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield b": heartbeat\n\n"
                continue
            if event.get("session_id") != session_id:
                continue
            yield f"data: {json.dumps(event)}\n\n".encode("utf-8")
    finally:
        activation_bus.unsubscribe(workspace_id, queue)


@router.get("/activation-stream")
async def activation_stream(
    request: Request,
    session_id: str = Query(..., min_length=1),
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    resolved_workspace = workspace_id or str(user.get("workspace_id") or "default")
    return StreamingResponse(_events(request, resolved_workspace, session_id), media_type="text/event-stream")

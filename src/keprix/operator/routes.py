"""Operator copilot HTTP routes."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.operator.context_bundle import build_operator_context
from keprix.operator.copilot import stream_operator_copilot_message

router = APIRouter(prefix="/api/operator", tags=["operator"])


class CopilotMessageBody(BaseModel):
    message: str = Field(..., min_length=1)
    workspace_id: str = "default"
    confirm_action: dict[str, Any] | None = None
    page_path: str | None = None
    page_label: str | None = None


@router.get("/context")
async def get_operator_context(
    workspace_id: str = "default",
    detail: str = "nav",
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    bundle = await build_operator_context(workspace_id, detail=detail)
    return bundle.to_dict()


@router.post("/copilot/message")
async def post_operator_copilot_message(
    body: CopilotMessageBody,
    _user: dict = Depends(get_current_user),
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[bytes]:
        async for event in stream_operator_copilot_message(
            body.message.strip(),
            workspace_id=body.workspace_id,
            confirm_action=body.confirm_action,
            page_path=body.page_path,
            page_label=body.page_label,
        ):
            yield (json.dumps(event) + "\n").encode("utf-8")

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")

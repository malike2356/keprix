"""Public agent app webhook routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.agent_apps.automation import run_webhook_token

router = APIRouter(prefix="/api/public/agent-apps", tags=["agent-apps-public"])


class WebhookRunBody(BaseModel):
    input: str = Field(default="", min_length=0)
    inputs: dict[str, Any] = Field(default_factory=dict)


@router.post("/hooks/{token}")
async def agent_app_webhook(token: str, body: WebhookRunBody, request: Request) -> dict[str, Any]:
    client_ip = request.client.host if request.client else None
    try:
        return run_webhook_token(
            token,
            input_text=body.input,
            inputs=body.inputs,
            client_ip=client_ip,
        )
    except LookupError as exc:
        raise HTTPException(status_code=401, detail="Invalid webhook token") from exc
    except PermissionError as exc:
        code = str(exc)
        if code == "agent_app.webhook_rate_limit":
            raise HTTPException(status_code=429, detail="Webhook rate limit exceeded") from exc
        raise HTTPException(status_code=403, detail="Webhook request denied") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

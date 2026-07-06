"""Review gateway HTTP routes."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from keprix.api.auth import require_api_auth
from keprix.review_gateway.page_renderer import (
    render_confirmation_page,
    render_gone_page,
    render_invalid_page,
    render_review_page,
)
from keprix.review_gateway.service import (
    cancel_review_request,
    create_review_request,
    lookup_request_by_token,
    new_csrf_token,
    submit_review_decision,
)
from keprix.review_gateway.store import get_review_store
from keprix.review_gateway.tokens import validate_review_token
from keprix.security.audit import hash_ip

api_router = APIRouter(prefix="/api/review-gateway", tags=["review-gateway"])
public_router = APIRouter(tags=["review-public"])

_rate_get: dict[str, list[float]] = defaultdict(list)
_rate_post: dict[str, list[float]] = defaultdict(list)
_csrf_tokens: dict[str, str] = {}


def _workspace_id(request: Request) -> str:
    return request.headers.get("x-workspace-id", "default").strip() or "default"


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _check_rate(bucket: dict[str, list[float]], key: str, limit: int, window: float = 3600.0) -> None:
    now = time.time()
    bucket[key] = [stamp for stamp in bucket[key] if now - stamp < window]
    if len(bucket[key]) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket[key].append(now)


class CreateReviewBody(BaseModel):
    title: str = Field(..., min_length=1)
    context_message: str = ""
    artifact_type: str = "markdown"
    artifact_content: str = ""
    artifact_url: str = ""
    artifact_filename: str = ""
    reviewer_name: str = Field(..., min_length=1)
    reviewer_email: str = Field(..., min_length=3)
    reviewer_webhook_url: str = ""
    allowed_actions: list[str] = Field(default_factory=lambda: ["approve", "reject"])
    expires_in_hours: int = Field(default=48, ge=1, le=720)
    reminder_in_hours: int | None = Field(default=None, ge=1, le=720)
    playbook_run_id: str | None = None
    playbook_step_id: str | None = None
    domain_pack: str = ""


@api_router.post("/requests")
async def create_request(
    body: CreateReviewBody,
    request: Request,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    req, url_token = await create_review_request(
        workspace_id=_workspace_id(request),
        title=body.title,
        context_message=body.context_message,
        artifact_type=body.artifact_type,
        artifact_content=body.artifact_content,
        artifact_url=body.artifact_url,
        artifact_filename=body.artifact_filename,
        reviewer_name=body.reviewer_name,
        reviewer_email=body.reviewer_email,
        reviewer_webhook_url=body.reviewer_webhook_url,
        allowed_actions=body.allowed_actions,
        expires_in_hours=body.expires_in_hours,
        reminder_in_hours=body.reminder_in_hours,
        playbook_run_id=body.playbook_run_id,
        playbook_step_id=body.playbook_step_id,
        domain_pack=body.domain_pack,
        created_by_user_id=user,
        base_url=_base_url(request),
    )
    return {
        "id": req.id,
        "review_url": f"{_base_url(request)}/review/{url_token}",
        "expires_at": req.expires_at,
        "token_id": req.token_id,
    }


@api_router.get("/requests")
async def list_requests(
    request: Request,
    status: str | None = None,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    rows = get_review_store().list_for_workspace(_workspace_id(request), status=status)
    return {"requests": [row.to_dict() for row in rows]}


@api_router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    request: Request,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    req = get_review_store().get(request_id)
    if req is None or req.workspace_id != _workspace_id(request):
        raise HTTPException(status_code=404, detail="Review request not found")
    return req.to_dict()


@api_router.delete("/requests/{request_id}")
async def delete_request(
    request_id: str,
    request: Request,
    _user: str = Depends(require_api_auth),
) -> dict[str, bool]:
    await cancel_review_request(request_id, _workspace_id(request))
    return {"ok": True}


@public_router.get("/review/{url_token}", response_class=HTMLResponse)
async def public_review_page(url_token: str, request: Request) -> HTMLResponse:
    _check_rate(_rate_get, url_token, 10)
    req = lookup_request_by_token(url_token)
    if req is None:
        return HTMLResponse(render_invalid_page(), status_code=404, headers=_public_headers())
    if req.status == "decided":
        return HTMLResponse(render_gone_page(), status_code=410, headers=_public_headers())
    from datetime import datetime

    expires = datetime.fromisoformat(req.expires_at)
    if not validate_review_token(
        url_token,
        token_id=req.token_id,
        review_request_id=req.id,
        workspace_id=req.workspace_id,
        expires_at=expires,
        status=req.status,
    ):
        return HTMLResponse(render_invalid_page(), status_code=404, headers=_public_headers())
    csrf = new_csrf_token()
    _csrf_tokens[url_token] = csrf
    html = render_review_page(
        req,
        workspace_name="Keprix",
        url_token=url_token,
        csrf_token=csrf,
    )
    return HTMLResponse(html, headers=_public_headers())


@public_router.post("/review/{url_token}", response_class=HTMLResponse)
async def public_review_submit(
    url_token: str,
    request: Request,
    action: str = Form(...),
    reviewer_note: str = Form(""),
    csrf_token: str = Form(""),
) -> HTMLResponse:
    _check_rate(_rate_post, url_token, 5)
    expected = _csrf_tokens.get(url_token)
    if not expected or csrf_token != expected:
        return HTMLResponse(render_invalid_page(), status_code=400, headers=_public_headers())
    ip_hash = hash_ip(request.client.host if request.client else "")
    try:
        await submit_review_decision(
            url_token=url_token,
            action=action,
            reviewer_note=reviewer_note[:2000],
            reviewer_ip_hash=ip_hash,
        )
    except HTTPException as exc:
        if exc.status_code == 410:
            return HTMLResponse(render_gone_page(), status_code=410, headers=_public_headers())
        return HTMLResponse(render_invalid_page(), status_code=exc.status_code, headers=_public_headers())
    _csrf_tokens.pop(url_token, None)
    return HTMLResponse(render_confirmation_page(action), headers=_public_headers())


def _public_headers() -> dict[str, str]:
    return {
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'self'",
    }

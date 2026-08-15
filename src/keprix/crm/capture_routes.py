"""Public CTA capture and authenticated capture-link management routes."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm.capture import create_capture_link, list_capture_links, rotate_capture_link, set_capture_link_active, submit_capture
from keprix.crm.roles import require_cap
from keprix.crm.routes import _store, _workspace

public_router = APIRouter(prefix="/capture", tags=["crm-capture-public"])
router = APIRouter(prefix="/api/crm/capture-links", tags=["crm-capture-links"])


class CaptureLinkCreate(BaseModel):
    label: str = ""
    default_source: str = "capture"
    redirect_url: str = ""


def _redirect_ok(value: str) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return (not parsed.scheme and not parsed.netloc and value.startswith("/")) or (parsed.scheme == "https" and bool(parsed.netloc))


def _page(token: str, *, error: str = "") -> str:
    message = f"<p role='alert'>{html.escape(error)}</p>" if error else ""
    return "<!doctype html><meta charset='utf-8'><title>Get in touch</title>" + message + """
    <form method="post" enctype="application/x-www-form-urlencoded">
      <label>Full name <input name="fullname" required maxlength="200"></label>
      <label>Email <input type="email" name="email" required maxlength="320"></label>
      <label>Company <input name="company" maxlength="200"></label>
      <label>Phone <input name="phone" maxlength="40"></label>
      <label><input type="checkbox" name="consent" value="yes" required>
        I agree to be contacted about this request.</label>
      <input name="website" tabindex="-1" autocomplete="off" aria-hidden="true" style="display:none">
      <button type="submit">Continue</button>
    </form>"""


@public_router.get("/{token}", response_class=HTMLResponse)
async def capture_form(token: str) -> HTMLResponse:
    return HTMLResponse(_page(token))


@public_router.post("/{token}")
async def capture_submit(token: str, request: Request) -> JSONResponse | HTMLResponse:
    content_type = request.headers.get("content-type", "")
    payload: dict[str, Any]
    if "application/json" in content_type:
        payload = await request.json()
        wants_json = True
    else:
        payload = dict(await request.form())
        wants_json = False
    if payload.get("website"):
        result = {"ok": True, "status": "ignored"}
    else:
        try:
            result = submit_capture(
                _store(), token, email=str(payload.get("email") or ""), fullname=str(payload.get("fullname") or ""),
                consent=str(payload.get("consent") or "").lower() in {"1", "true", "yes", "on"},
                ip=request.client.host if request.client else "", company=str(payload.get("company") or ""), phone=str(payload.get("phone") or ""),
                source=str(payload.get("source") or ""), campaign=str(payload.get("campaign") or ""), utm=str(payload.get("utm") or ""), referrer=request.headers.get("referer", ""),
            )
        except (ValueError, LookupError, PermissionError) as exc:
            if wants_json:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return HTMLResponse(_page(token, error=str(exc)), status_code=400)
    if wants_json:
        return JSONResponse(result)
    redirect_url = result.get("redirect_url") or "/"
    if not _redirect_ok(redirect_url):
        redirect_url = "/"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(redirect_url, status_code=303)


@router.post("")
async def create_link(body: CaptureLinkCreate, workspace_id: str | None = None, x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "edit")
    if not _redirect_ok(body.redirect_url):
        raise HTTPException(status_code=422, detail="redirect_url must be a same-origin path or HTTPS URL")
    return create_capture_link(_store(), _workspace(workspace_id, x_workspace_id, user), label=body.label, default_source=body.default_source, redirect_url=body.redirect_url)


@router.get("")
async def get_links(workspace_id: str | None = None, x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    return {"items": list_capture_links(_store(), _workspace(workspace_id, x_workspace_id, user))}


@router.post("/{link_id}/rotate")
async def rotate_link(link_id: str, workspace_id: str | None = None, x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "edit")
    result = rotate_capture_link(_store(), _workspace(workspace_id, x_workspace_id, user), link_id)
    if result is None:
        raise HTTPException(status_code=404, detail="capture link not found")
    return result


@router.post("/{link_id}/disable")
async def disable_link(link_id: str, workspace_id: str | None = None, x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "edit")
    ok = set_capture_link_active(_store(), _workspace(workspace_id, x_workspace_id, user), link_id, False)
    if not ok:
        raise HTTPException(status_code=404, detail="capture link not found")
    return {"ok": True, "active": False, "id": link_id}

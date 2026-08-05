"""Google Workspace connector API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.connections_service import ConnectionsService
from keprix.auth.dependencies import get_current_user
from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge, GoogleWorkspaceError

router = APIRouter(prefix="/api/integrations/google-workspace", tags=["integrations"])


class OAuthStartBody(BaseModel):
    redirect_uri: str | None = None


class OAuthCallbackBody(BaseModel):
    code: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: str | None = None
    account_email: str | None = None
    scopes: list[str] | None = None
    workspace_id: str = "personal-os"
    workspace_path: str | None = None


class GmailListBody(BaseModel):
    query: str = ""
    max_results: int = Field(default=10, ge=1, le=100)


class GmailSendBody(BaseModel):
    to: str
    subject: str
    body: str
    confirm: bool = False


class CalendarListBody(BaseModel):
    time_min: str | None = None
    max_results: int = Field(default=10, ge=1, le=100)


class CalendarCreateBody(BaseModel):
    summary: str
    start: str
    end: str
    attendees: list[str] = Field(default_factory=list)
    confirm: bool = False


class DriveSearchBody(BaseModel):
    query: str
    max_results: int = Field(default=10, ge=1, le=100)


class SheetsReadBody(BaseModel):
    spreadsheet_id: str
    range: str = "Sheet1!A1:Z100"


def _bridge() -> GoogleWorkspaceBridge:
    return GoogleWorkspaceBridge()


def _handle(call):
    try:
        return call()
    except GoogleWorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _mark_connections_live(workspace_id: str, workspace_path: str | None) -> None:
    service = ConnectionsService()
    for domain in ("calendar", "comms", "knowledge"):
        try:
            service.update_domain(
                domain,
                status="live",
                tools=["gws_gmail_list", "gws_calendar_list", "gws_drive_search"],
                integration_ref="google-workspace",
                service_account=True,
                workspace_id=workspace_id,
                workspace_path=workspace_path,
            )
        except ValueError:
            continue


@router.get("/status")
async def status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _bridge().status()


@router.post("/oauth/start")
async def oauth_start(body: OAuthStartBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _handle(lambda: _bridge().auth_url(redirect_uri=body.redirect_uri or "http://localhost:8751/api/integrations/google-workspace/oauth/callback"))


@router.post("/oauth/callback")
async def oauth_callback(body: OAuthCallbackBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    result = _handle(lambda: _bridge().exchange_callback(body.model_dump(exclude_none=True)))
    _mark_connections_live(body.workspace_id, body.workspace_path)
    return result


@router.delete("")
async def logout(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _bridge().logout()


@router.post("/gmail/list")
async def gmail_list(body: GmailListBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _handle(lambda: _bridge().gmail_list(query=body.query, max_results=body.max_results))


@router.post("/gmail/send")
async def gmail_send(body: GmailSendBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _handle(lambda: _bridge().gmail_send(to=body.to, subject=body.subject, body=body.body, confirm=body.confirm))


@router.post("/calendar/list")
async def calendar_list(body: CalendarListBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _handle(lambda: _bridge().calendar_list(time_min=body.time_min, max_results=body.max_results))


@router.post("/calendar/create")
async def calendar_create(body: CalendarCreateBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _handle(lambda: _bridge().calendar_create(summary=body.summary, start=body.start, end=body.end, attendees=body.attendees, confirm=body.confirm))


@router.post("/drive/search")
async def drive_search(body: DriveSearchBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _handle(lambda: _bridge().drive_search(query=body.query, max_results=body.max_results))


@router.post("/sheets/read")
async def sheets_read(body: SheetsReadBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return _handle(lambda: _bridge().sheets_read(spreadsheet_id=body.spreadsheet_id, range_name=body.range))

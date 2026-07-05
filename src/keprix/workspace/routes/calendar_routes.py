"""Calendar workspace routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.auth.dependencies import get_current_user
from keprix.workspace.caldav_sync import sync_caldav
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import CaldavSourceCreate, CalendarEventCreate, CalendarEventUpdate

router = APIRouter(prefix="/api/workspace/calendar", tags=["workspace-calendar"])


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username"))


@router.post("/events", status_code=201)
async def create_event(body: CalendarEventCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.create_event(user, **body.model_dump())


@router.get("/events")
async def list_events(
    user: dict = Depends(get_current_user),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> dict[str, Any]:
    rows = workspace_repo.list_events(user, start=start, end=end)
    return {"items": rows}


@router.get("/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return workspace_repo.get_event(user, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    body: CalendarEventUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return workspace_repo.update_event(user, event_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None


@router.delete("/events/{event_id}", status_code=200)
async def delete_event(event_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_event(user, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None


@router.post("/sync")
async def trigger_sync(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sources = workspace_repo.list_caldav_sources(user)
    return await sync_caldav(_user_id(user), sources)


@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": workspace_repo.list_caldav_sources(user)}


@router.post("/sources", status_code=201)
async def add_source(body: CaldavSourceCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.add_caldav_source(user, **body.model_dump())

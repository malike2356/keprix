"""Calendar workspace routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.auth.dependencies import get_current_user
from keprix.workspace.calendar_sync import PROVIDER_PRESETS, push_event_to_source, sync_caldav, sync_one_source
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import CaldavSourceCreate, CaldavSourceUpdate, CalendarEventCreate, CalendarEventUpdate

router = APIRouter(prefix="/api/workspace/calendar", tags=["workspace-calendar"])


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username"))


async def _maybe_push_event(user: dict, event: dict[str, Any]) -> dict[str, Any]:
    source = workspace_repo.default_push_source(user)
    if not source:
        return event
    try:
        ok = await push_event_to_source(user, source, event, workspace_repo)
        if ok:
            return workspace_repo.update_event(
                user,
                event["id"],
                caldav_source_id=source["id"],
                external_etag=True,
            )
    except Exception:
        pass
    return event


@router.post("/events", status_code=201)
async def create_event(body: CalendarEventCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    event = workspace_repo.create_event(user, **body.model_dump())
    return await _maybe_push_event(user, event)


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
        event = workspace_repo.update_event(user, event_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None
    if event.get("external_readonly"):
        return event
    return await _maybe_push_event(user, event)


@router.delete("/events/{event_id}", status_code=200)
async def delete_event(event_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_event(user, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None


@router.get("/providers")
async def list_providers(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": PROVIDER_PRESETS}


@router.get("/auto-sync")
async def auto_sync_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from keprix.workspace.calendar_sync_scheduler import scheduler_status

    return scheduler_status()


@router.post("/sync")
async def trigger_sync(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sources = workspace_repo.list_caldav_sources(user)
    return await sync_caldav(_user_id(user), sources)


@router.post("/sources/{source_id}/sync")
async def sync_source(source_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        source = workspace_repo.get_caldav_source(user, source_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found") from None
    try:
        outcome = await sync_one_source(user, source, workspace_repo)
        workspace_repo.mark_source_synced(user, source_id, ok=True, message=outcome.get("message"))
        return outcome
    except Exception as exc:
        message = str(exc)
        workspace_repo.mark_source_synced(user, source_id, ok=False, message=message)
        raise HTTPException(status_code=400, detail=message) from None


@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": workspace_repo.list_caldav_sources(user)}


@router.post("/sources", status_code=201)
async def add_source(body: CaldavSourceCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    data = body.model_dump()
    provider = str(data.get("provider") or "caldav").lower()
    if provider == "ics" and not str(data.get("url") or "").strip():
        raise HTTPException(status_code=400, detail="ICS feed URL is required")
    if provider != "ics" and not str(data.get("url") or "").strip() and not (
        provider == "google" and str(data.get("username") or "").strip()
    ):
        raise HTTPException(status_code=400, detail="CalDAV URL is required (or Google email as username)")
    if provider != "ics" and not data.get("password") and not data.get("vault_item_id"):
        raise HTTPException(status_code=400, detail="Password or access token is required for CalDAV sync")
    if provider == "ics":
        data["sync_direction"] = "pull"
        data["push_local_events"] = False
    elif data.get("push_local_events") is None and str(data.get("sync_direction") or "bidirectional") in {
        "bidirectional",
        "push",
    }:
        data["push_local_events"] = True
    source = workspace_repo.add_caldav_source(user, **data)
    return source


@router.patch("/sources/{source_id}")
async def update_source(
    source_id: str,
    body: CaldavSourceUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return workspace_repo.update_caldav_source(user, source_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found") from None


@router.delete("/sources/{source_id}", status_code=200)
async def delete_source(
    source_id: str,
    user: dict = Depends(get_current_user),
    remove_events: bool = Query(False),
) -> dict[str, Any]:
    try:
        workspace_repo.delete_caldav_source(user, source_id, remove_events=remove_events)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found") from None
    return {"ok": True, "id": source_id}

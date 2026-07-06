"""Notifications HTTP routes (Prompt 24)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.backend.notifications.digest import get_digest_service
from keprix.backend.notifications.push import get_push_service, get_push_token_store
from keprix.backend.notifications.delivery import get_delivery_service
from keprix.backend.notifications.escalation import get_escalation_service
from keprix.backend.notifications.inbox import get_inbox_service
from keprix.backend.notifications.preferences import get_preferences_service
from keprix.backend.notifications.schemas import NotificationDispatchBody, PreferencesUpdateBody

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


@router.get("/inbox")
async def list_inbox(
    workspace_id: str = "default",
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    rows = get_inbox_service().list_inbox(
        workspace_id,
        user_id=_user_id(user),
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    unread = get_inbox_service().unread_count(workspace_id, _user_id(user))
    return {"notifications": rows, "unread_count": unread, "count": len(rows)}


@router.get("/inbox/{notification_id}")
async def get_inbox_item(
    notification_id: str,
    workspace_id: str = "default",
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    row = get_inbox_service().get_notification(workspace_id, notification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"notification": row}


@router.post("/inbox/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    workspace_id: str = "default",
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    row = get_inbox_service().mark_read(workspace_id, notification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"notification": row}


@router.post("/inbox/read-all")
async def mark_all_read(
    workspace_id: str = "default",
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    count = get_inbox_service().mark_all_read(workspace_id, _user_id(user))
    return {"marked_read": count}


@router.get("/preferences")
async def get_preferences(
    workspace_id: str = "default",
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return get_preferences_service().get(workspace_id, _user_id(user))


@router.put("/preferences")
async def update_preferences(
    body: PreferencesUpdateBody,
    workspace_id: str = "default",
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    return get_preferences_service().update(workspace_id, _user_id(user), patch)


@router.post("/dispatch")
async def dispatch_notification(
    body: NotificationDispatchBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        notification = await get_inbox_service().send_notification(
            body.workspace_id,
            body.notification_type,
            severity=body.severity,
            title=body.title,
            message=body.message,
            user_id=body.user_id,
            href=body.href,
            sensitive=body.sensitive,
            metadata=body.metadata,
            source=body.source,
            source_id=body.source_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"notification": notification}


@router.post("/escalations/process")
async def process_escalations(
    workspace_id: str = "default",
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    processed = await get_escalation_service().process_due_escalations(workspace_id)
    return {"processed": processed, "count": len(processed)}


@router.post("/deliveries/retry")
async def retry_deliveries(
    workspace_id: str = "default",
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    results = await get_delivery_service().retry_failed_deliveries(workspace_id)
    return {"retries": results, "count": len(results)}


class PushRegisterBody(BaseModel):
    platform: str = Field(..., pattern="^(ios|android)$")
    token: str = Field(..., min_length=8)
    device_name: str | None = None
    workspace_id: str = "default"


class PushSendBody(BaseModel):
    title: str
    message: str
    workspace_id: str = "default"
    user_id: str | None = None
    platform: str | None = None


@router.post("/register")
async def register_push_token(
    body: PushRegisterBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    row = get_push_token_store().register(
        workspace_id=body.workspace_id,
        user_id=_user_id(user),
        platform=body.platform,
        token=body.token,
        device_name=body.device_name,
    )
    return {"device": row}


@router.post("/send")
async def send_push_notification(
    body: PushSendBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = await get_push_service().send(
        workspace_id=body.workspace_id,
        title=body.title,
        message=body.message,
        user_id=body.user_id,
        platform=body.platform,
    )
    return result


@router.post("/digest/flush")
async def flush_digest(
    workspace_id: str = "default",
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return await get_digest_service().flush_digest_queue(workspace_id, _user_id(user))

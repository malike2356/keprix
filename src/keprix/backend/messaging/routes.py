"""Room configuration and ambient messaging routes (Prompt 45)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.backend.messaging.room_config import CHANNELS_SUPPORTING_ALWAYS_ON, get_room_config_store
from keprix.backend.messaging.schemas import InboundMessage
from keprix.backend.messaging.gateway import get_message_gateway

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


class RoomConfigPatch(BaseModel):
    channel_type: str | None = None
    unmentioned_inbound: str | None = None
    visible_replies: str | None = None
    history_limit: int | None = None
    mention_gating: bool | None = None
    always_on: bool | None = None


class AmbientEnableBody(BaseModel):
    workspace_id: str = "default"
    channel_type: str = "whatsapp"


class DispatchBody(BaseModel):
    workspace_id: str = "default"
    channel_type: str = "whatsapp"
    message_id: str = Field(min_length=1)
    sender_id: str = "user"
    sender_name: str = "User"
    text: str = Field(min_length=1)
    is_mention: bool = False
    is_group: bool = True


@router.get("")
async def list_rooms(workspace_id: str = "default", _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rooms = get_room_config_store().list_rooms(workspace_id)
    return {
        "rooms": [
            {
                **room.to_dict(),
                "supports_always_on": room.channel_type in CHANNELS_SUPPORTING_ALWAYS_ON,
            }
            for room in rooms
        ],
        "count": len(rooms),
    }


@router.get("/{room_id}/config")
async def get_room_config(
    room_id: str,
    workspace_id: str = "default",
    channel_type: str = "unknown",
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    config = get_room_config_store().get(workspace_id, room_id, channel_type=channel_type)
    return {
        **config.to_dict(),
        "supports_always_on": config.channel_type in CHANNELS_SUPPORTING_ALWAYS_ON,
    }


@router.patch("/{room_id}/config")
async def patch_room_config(
    room_id: str,
    body: RoomConfigPatch,
    workspace_id: str = "default",
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    store = get_room_config_store()
    current = store.get(workspace_id, room_id, channel_type=body.channel_type or "unknown")
    if body.always_on and current.channel_type not in CHANNELS_SUPPORTING_ALWAYS_ON:
        raise HTTPException(status_code=422, detail="Channel does not support always-on mode")
    updated = store.update(
        workspace_id,
        room_id,
        channel_type=body.channel_type or current.channel_type,
        unmentioned_inbound=body.unmentioned_inbound,
        visible_replies=body.visible_replies,
        history_limit=body.history_limit,
        mention_gating=body.mention_gating,
        always_on=body.always_on,
    )
    return {
        **updated.to_dict(),
        "supports_always_on": updated.channel_type in CHANNELS_SUPPORTING_ALWAYS_ON,
    }


@router.post("/{room_id}/config/ambient")
async def enable_ambient_mode(
    room_id: str,
    body: AmbientEnableBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    updated = get_room_config_store().enable_ambient(body.workspace_id, room_id, channel_type=body.channel_type)
    return {
        **updated.to_dict(),
        "supports_always_on": updated.channel_type in CHANNELS_SUPPORTING_ALWAYS_ON,
    }


@router.post("/{room_id}/dispatch")
async def dispatch_room_message(
    room_id: str,
    body: DispatchBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    message = InboundMessage(
        room_id=room_id,
        workspace_id=body.workspace_id,
        channel_type=body.channel_type,
        message_id=body.message_id,
        sender_id=body.sender_id,
        sender_name=body.sender_name,
        text=body.text,
        is_mention=body.is_mention,
        is_group=body.is_group,
    )
    result = await get_message_gateway().dispatch_for_room(message)
    return {
        "handled": result.handled,
        "replied": result.replied,
        "mode": result.mode,
        "ambient_should_reply": result.ambient_result.should_reply if result.ambient_result else None,
    }

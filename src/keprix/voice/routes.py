"""HTTP routes for gateway-owned wake words (Prompt 46)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from keprix.auth.dependencies import get_current_user
from keprix.voice.bus import list_node_statuses
from keprix.voice.schemas import (
    NodeWakeStatusList,
    NodeWakeStatusOut,
    WakeWordRoutingConfigOut,
    WakeWordRoutingUpdate,
    WakeWordsOut,
    WakeWordsUpdate,
)
from keprix.voice.service import get_wake_registry
from keprix.voice.wake import WakeWordRoutingConfig

router = APIRouter(prefix="/api/voice/wake-words", tags=["voice-wake"])


def _wake_words_out() -> WakeWordsOut:
    registry = get_wake_registry()
    routing = registry.get_routing()
    return WakeWordsOut(
        triggers=registry.get(),
        routing=WakeWordRoutingConfigOut(**routing.to_dict()),
    )


@router.get("")
async def get_wake_words(_user: dict = Depends(get_current_user)) -> WakeWordsOut:
    return _wake_words_out()


@router.put("")
async def put_wake_words(body: WakeWordsUpdate, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    saved = get_wake_registry().set(body.triggers)
    return {"triggers": saved}


@router.get("/routing")
async def get_wake_routing(_user: dict = Depends(get_current_user)) -> WakeWordRoutingConfigOut:
    routing = get_wake_registry().get_routing()
    return WakeWordRoutingConfigOut(**routing.to_dict())


@router.put("/routing")
async def put_wake_routing(
    body: WakeWordRoutingUpdate,
    _user: dict = Depends(get_current_user),
) -> WakeWordRoutingConfigOut:
    saved = get_wake_registry().set_routing(WakeWordRoutingConfig.from_dict(body.model_dump()))
    return WakeWordRoutingConfigOut(**saved.to_dict())


@router.post("/reset")
async def reset_wake_words(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    saved = get_wake_registry().reset()
    return {"triggers": saved}


@router.get("/nodes")
async def list_wake_nodes(_user: dict = Depends(get_current_user)) -> NodeWakeStatusList:
    nodes = [NodeWakeStatusOut(**row) for row in list_node_statuses()]
    return NodeWakeStatusList(nodes=nodes)

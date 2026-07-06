"""JSON-RPC handlers for voicewake gateway methods."""

from __future__ import annotations

from typing import Any, Callable

from keprix.voice.activation import new_voice_session_id, resolve_activation_target
from keprix.voice.bus import broadcast, list_node_statuses, register_node_status
from keprix.voice.service import get_wake_registry
from keprix.voice.wake import WakeWordRoutingConfig


def _ok(rid: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _err(rid: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def voicewake_get(rid: Any, params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    registry = get_wake_registry()
    return _ok(rid, {"triggers": registry.get()})


def voicewake_set(rid: Any, params: dict[str, Any]) -> dict[str, Any]:
    triggers = params.get("triggers")
    if not isinstance(triggers, list):
        return _err(rid, -32602, "voicewake.set requires triggers: string[]")
    registry = get_wake_registry()
    saved = registry.set([str(item) for item in triggers])
    return _ok(rid, {"triggers": saved})


def voicewake_routing_get(rid: Any, params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    registry = get_wake_registry()
    return _ok(rid, {"config": registry.get_routing().to_dict()})


def voicewake_routing_set(rid: Any, params: dict[str, Any]) -> dict[str, Any]:
    config = params.get("config")
    if not isinstance(config, dict):
        return _err(rid, -32602, "voicewake.routing.set requires config: object")
    registry = get_wake_registry()
    saved = registry.set_routing(WakeWordRoutingConfig.from_dict(config))
    return _ok(rid, {"config": saved.to_dict()})


def voicewake_triggered(rid: Any, params: dict[str, Any]) -> dict[str, Any]:
    node_id = str(params.get("node_id") or "unknown")
    trigger_phrase = str(params.get("trigger_phrase") or "")
    active_session_id = params.get("active_session_id")
    registry = get_wake_registry()
    routing = registry.get_routing()
    target = resolve_activation_target(
        routing,
        node_id=node_id,
        active_session_id=str(active_session_id) if active_session_id else None,
    )
    session_id = new_voice_session_id()
    payload = {
        "method": "voicewake.session_start",
        "session_id": session_id,
        "node_id": node_id,
        "trigger_phrase": trigger_phrase,
        "target": target,
    }
    broadcast(payload)
    return _ok(
        rid,
        {
            "session_id": session_id,
            "node_id": node_id,
            "trigger_phrase": trigger_phrase,
            "target": target,
        },
    )


def voicewake_node_status(rid: Any, params: dict[str, Any]) -> dict[str, Any]:
    node_id = str(params.get("node_id") or "")
    if not node_id:
        return _err(rid, -32602, "voicewake.node.status requires node_id")
    platform = str(params.get("platform") or "desktop")
    wake_enabled = bool(params.get("wake_enabled", False))
    permission_granted = bool(params.get("permission_granted", False))
    register_node_status(
        node_id,
        platform=platform,
        wake_enabled=wake_enabled,
        permission_granted=permission_granted,
    )
    return _ok(rid, {"registered": True})


def voicewake_nodes_list(rid: Any, params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    return _ok(rid, {"nodes": list_node_statuses()})


VOICEWAKE_METHODS: dict[str, Callable[[Any, dict[str, Any]], dict[str, Any]]] = {
    "voicewake.get": voicewake_get,
    "voicewake.set": voicewake_set,
    "voicewake.routing.get": voicewake_routing_get,
    "voicewake.routing.set": voicewake_routing_set,
    "voicewake.triggered": voicewake_triggered,
    "voicewake.node.status": voicewake_node_status,
    "voicewake.nodes.list": voicewake_nodes_list,
}


def register_voicewake_methods(target: dict[str, Callable[[Any, dict[str, Any]], dict[str, Any]]]) -> None:
    target.update(VOICEWAKE_METHODS)


def try_register_with_tui_gateway() -> bool:
    try:
        from tui_gateway import server
    except ImportError:
        return False
    register_voicewake_methods(server._methods)
    return True

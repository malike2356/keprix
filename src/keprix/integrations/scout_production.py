"""Production Scout connectivity, health, and verification helpers."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from keprix.security.scout_client import get_scout_client, refresh_scout_client
from keprix.security.scout_config import ScoutConfig, resolve_scout_config
from keprix.security.scout_types import SignalCategory, SignalSeverity

_LAST_PING_AT: str | None = None
_LAST_PING_OK: bool | None = None


def scout_runtime_config() -> ScoutConfig:
    return resolve_scout_config()


async def scout_ping(*, timeout: float = 10.0) -> dict[str, Any]:
    global _LAST_PING_AT, _LAST_PING_OK
    config = scout_runtime_config()
    started = time.perf_counter()
    if not config.enabled or not config.api_key:
        return {
            "ok": False,
            "reachable": False,
            "reason": "scout disabled or missing api key",
            "agent_id": config.agent_id,
            "endpoint": config.endpoint,
        }

    client = await refresh_scout_client()
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    if config.agent_id:
        headers["X-Agent-Id"] = config.agent_id

    heartbeat_url = f"{config.endpoint.rstrip('/')}/api/v1/heartbeat"
    body = json.dumps(
        {
            "instance_id": config.agent_id or "keprix-local",
            "version": "probe",
            "uptime_seconds": 0,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
    ).encode("utf-8")
    ok = False
    status_code = 0
    error: str | None = None
    try:
        from keprix.governance.signing import sign_payload

        headers["X-Governance-Signature"] = f"sha256={sign_payload(config.api_key, body)}"
        async with httpx.AsyncClient(timeout=timeout) as http:
            response = await http.post(heartbeat_url, content=body, headers=headers)
        status_code = response.status_code
        ok = status_code < 400
        if not ok:
            error = response.text[:300]
    except Exception as exc:
        error = str(exc)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    _LAST_PING_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _LAST_PING_OK = ok
    return {
        "ok": ok,
        "reachable": ok,
        "status_code": status_code,
        "latency_ms": elapsed_ms,
        "agent_id": config.agent_id or f"keprix:{config.product}:local",
        "endpoint": config.endpoint,
        "error": error,
    }


async def scout_test_signal(*, timeout: float = 10.0) -> dict[str, Any]:
    config = scout_runtime_config()
    if not config.enabled or not config.api_key:
        return {"ok": False, "reason": "scout disabled or missing api key"}

    client = await refresh_scout_client()
    await client.start()
    started = time.perf_counter()
    client.send(
        SignalCategory.GOVERNANCE,
        SignalSeverity.INFO,
        "upstream.probe",
        "scout:test-signal",
        {"probe": True, "source": "keprix scout test-signal"},
        correlation_id="scout-test-signal",
    )
    before = client.pending_count()
    await client._flush()
    after = client.pending_count()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await client.stop()
    flushed = before > after or before == 0
    return {
        "ok": flushed,
        "flushed": flushed,
        "latency_ms": elapsed_ms,
        "pending_before": before,
        "pending_after": after,
        "agent_id": config.agent_id,
    }


async def scout_test_command(*, timeout: float = 5.0) -> dict[str, Any]:
    config = scout_runtime_config()
    from keprix.security.scout_listener import ScoutListener
    from keprix.security.scout_types import ScoutCommand

    listener = ScoutListener(config)
    payload = {
        "command_id": "scout-test-command",
        "command": ScoutCommand.SET_RATE_LIMIT.value,
        "agent_id": config.agent_id or "*",
        "session_id": None,
        "params": {"calls_per_minute": 120},
        "issued_by": "keprix-scout-test",
        "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    started = time.perf_counter()
    result = await listener.handle_message(json.dumps(payload))
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "ok": result is not None and result.get("status") == "executed",
        "result": result,
        "latency_ms": elapsed_ms,
        "listener_enabled": listener.enabled,
    }


async def scout_health_payload() -> dict[str, Any]:
    config = scout_runtime_config()
    client = get_scout_client()
    from keprix.security.scout_sync import get_scout_sync

    sync = get_scout_sync()
    return {
        "enabled": config.enabled,
        "connected": bool(_LAST_PING_OK),
        "endpoint": config.endpoint,
        "agent_id": config.agent_id,
        "redis_url_configured": bool(config.redis_url),
        "signals_buffered": client.pending_count(),
        "last_ping_at": _LAST_PING_AT,
        "sync_enabled": sync.enabled,
    }


def security_layers_payload() -> dict[str, Any]:
    from keprix.security.prompt_guard_policy import prompt_guard_mode
    from keprix.security.tool_acl import get_tool_acl

    acl = get_tool_acl()
    base_acl = acl.snapshot().get(acl.BASE_PRODUCT, {})
    prompt_mode = prompt_guard_mode()
    layers: dict[str, Any] = {
        "prompt_guard": {
            "present": True,
            "mode": prompt_mode,
            "enforced": prompt_mode != "log",
        },
        "egress_gate": {
            "present": True,
            "enforced": True,
        },
        "tool_acl": {
            "present": True,
            "base_allow_all": "*" in list(base_acl.get("allowed_tools", [])),
            "enforced": True,
            "default_profile": "assistant",
        },
        "checkpoint_manager": {
            "present": True,
            "enabled": True,
        },
        "scout_client": {
            "present": True,
            "enabled": scout_runtime_config().enabled,
        },
    }
    try:
        from keprix.governance.kill_relay import get_kill_state

        layers["governance_kill_relay"] = True
        layers["kill_state"] = get_kill_state().to_dict()
    except Exception:
        layers["governance_kill_relay"] = False
    try:
        from keprix.governance.policy_receiver import get_policy_registry

        layers["governance_policy_registry"] = get_policy_registry().snapshot()
    except Exception:
        pass
    try:
        from keprix.security.scout_control import snapshot as control_snapshot

        layers["scout_control"] = control_snapshot()
    except Exception:
        pass
    return layers


def products_health_payload() -> dict[str, Any]:
    from keprix.integrations.product_registry import list_registered_products

    products = list_registered_products()
    return {
        "count": len(products),
        "products": products,
    }


def run_async(coro):
    return asyncio.run(coro)

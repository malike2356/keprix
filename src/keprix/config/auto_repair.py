"""Automatic repair actions triggered by health status changes."""

from __future__ import annotations

import asyncio

from keprix.config.health_monitor import ComponentHealth
from keprix.security.event_reporter import report_security_event

REPAIR_TIMEOUT_SECONDS = 120


async def handle_health_change(health: ComponentHealth) -> None:
    if health.status == "healthy":
        return

    name = health.name

    if name.startswith("llm:"):
        await _repair_llm_provider(name.removeprefix("llm:"), health.error)
    elif name == "redis":
        await _repair_redis(health.error)
    elif name.startswith("channel:"):
        await _repair_channel_adapter(name.removeprefix("channel:"), health.error)
    elif name.startswith("egress:"):
        await _alert_egress_failure(name, health.error)


async def repair_all_components(monitor) -> None:
    """Run health checks and attempt repair for every unhealthy component."""
    await monitor._run_all_checks()
    for health in monitor.get_all().values():
        if health.status != "healthy":
            await handle_health_change(health)


async def _repair_llm_provider(provider_name: str, error: str) -> None:
    from keprix.brain.llm_router import LLMRouter

    router = LLMRouter.get_instance()
    router.demote_provider(provider_name, reason=error)

    await report_security_event(
        "config_auto_repair",
        "warning",
        {
            "action": "llm_provider_demoted",
            "provider": provider_name,
            "reason": error[:200],
            "new_primary": router.current_primary(),
        },
    )


async def _repair_redis(error: str) -> None:
    from keprix.db.memory_fallback import activate_memory_fallback
    from keprix.db.redis_client import reconnect_redis

    for attempt in range(5):
        await asyncio.sleep(2**attempt)
        try:
            await reconnect_redis()
            await report_security_event(
                "config_auto_repair",
                "info",
                {
                    "action": "redis_reconnected",
                    "attempt": attempt + 1,
                },
            )
            return
        except Exception:
            continue

    activate_memory_fallback()
    await report_security_event(
        "config_auto_repair",
        "critical",
        {
            "action": "redis_fallback_activated",
            "note": (
                "Redis unreachable after 5 attempts. Running on in-memory cache. "
                "Data will be lost on restart."
            ),
        },
    )


async def _repair_channel_adapter(adapter_name: str, error: str) -> None:
    from keprix.gateway.adapter_registry import get_adapter

    adapter = get_adapter(adapter_name)
    if not adapter:
        return
    for attempt in range(3):
        await asyncio.sleep(5 * (attempt + 1))
        try:
            await adapter.reconnect()
            await report_security_event(
                "config_auto_repair",
                "info",
                {
                    "action": "channel_reconnected",
                    "adapter": adapter_name,
                    "attempt": attempt + 1,
                },
            )
            return
        except Exception:
            continue
    await report_security_event(
        "config_auto_repair",
        "warning",
        {
            "action": "channel_repair_failed",
            "adapter": adapter_name,
            "note": "Manual reconnection required. Check adapter credentials.",
        },
    )


async def _alert_egress_failure(name: str, error: str) -> None:
    await report_security_event(
        "config_auto_repair",
        "warning",
        {
            "action": "egress_host_unreachable",
            "host": name,
            "error": error[:200],
            "note": (
                "Check network connectivity and DNS. If persistent, verify the allowlist."
            ),
        },
    )

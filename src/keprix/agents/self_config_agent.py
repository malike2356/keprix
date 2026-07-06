"""Natural-language self-configuration request handling."""

from __future__ import annotations

from keprix.config.health_monitor import ConfigHealthMonitor
from keprix.config.optimizer import _load_pending_proposals
from keprix.security.event_reporter import report_security_event

SELF_CONFIG_KEYWORDS = frozenset(
    {
        "configure yourself",
        "configure keprix",
        "switch provider",
        "change provider",
        "use groq",
        "use deepseek",
        "use openai",
        "turn off",
        "disable channel",
        "enable channel",
        "clear old memories",
        "check your health",
        "health check",
        "what's wrong with you",
        "low memory mode",
        "optimize yourself",
    }
)


def is_self_config_request(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in SELF_CONFIG_KEYWORDS)


async def handle_self_config_request(
    text: str,
    session_id: str,
    authorized_by: str,
) -> str:
    """Route natural language self-config requests to the appropriate subsystem."""
    lowered = text.lower()

    if "health" in lowered or "what's wrong" in lowered:
        monitor = ConfigHealthMonitor()
        await monitor._run_all_checks()
        results = monitor.get_all()
        unhealthy = [item for item in results.values() if item.status != "healthy"]
        if not unhealthy:
            return "All components are healthy."
        lines = ["The following components have issues:"]
        for item in unhealthy:
            lines.append(f"- {item.name}: {item.status} ({item.error[:100]})")
        return "\n".join(lines)

    if "proposals" in lowered or "optimize" in lowered:
        pending = _load_pending_proposals()
        if not pending:
            return "No pending optimization proposals."
        lines = [f"{len(pending)} proposal(s) pending:"]
        for proposal in pending[:5]:
            lines.append(f"- [{proposal['proposal_id']}] {proposal['description']}")
        return "\n".join(lines)

    await report_security_event(
        "self_config_request",
        "info",
        {
            "text_preview": text[:200],
            "authorized_by": authorized_by,
            "session_id": session_id,
            "note": "Self-config request routed to natural language handler",
        },
    )

    return (
        "I can help reconfigure myself. For safety, complex configuration changes "
        "require using the CLI: `keprix configure` or `keprix proposals`. "
        "For quick changes like switching providers, please confirm: "
        f"did you want me to {text[:80]}? Reply 'yes' to confirm."
    )

"""Optional Scout bridge for Channel Shield events and commands."""

from __future__ import annotations

from typing import Any

from keprix.channel_shield.config import load_channel_shield_config
from keprix.channel_shield.types import PipelineReport, ShieldEnvelope, Verdict


def scout_configured() -> bool:
    try:
        from keprix.security.scout_config import get_scout_config

        cfg = get_scout_config()
        return bool(getattr(cfg, "enabled", False) or getattr(cfg, "api_key", None))
    except Exception:
        return bool(
            __import__("os").environ.get("SCOUT_ENABLED", "").strip().lower()
            in {"1", "true", "yes", "on"}
        )


def emit_shield_signal(
    action: str,
    envelope: ShieldEnvelope,
    *,
    report: PipelineReport | None = None,
    message_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str | None:
    """Emit Scout signal when configured; return local correlation id."""
    cfg = load_channel_shield_config()
    if not cfg.scout_emit_signals:
        return None
    if not scout_configured():
        return None

    severity_map = {
        Verdict.CLEAN: "info",
        Verdict.SUSPECT: "warning",
        Verdict.MALICIOUS: "critical",
        Verdict.ERROR: "high",
    }
    verdict = report.verdict if report else Verdict.CLEAN
    threat = report.threat_score if report else 0.0
    details = {
        "channel": envelope.channel,
        "protection_id": envelope.protection_id,
        "external_message_id": envelope.external_message_id,
        "message_id": message_id,
        "verdict": verdict.value,
        "threat_score": threat,
        **(extra or {}),
    }
    correlation = f"channel_shield:{envelope.channel}:{message_id or envelope.external_message_id}"
    try:
        from keprix.security.scout_integration import emit_scout_signal
        from keprix.security.scout_types import SignalCategory, SignalSeverity

        sev_name = severity_map.get(verdict, "warning").upper()
        severity = getattr(SignalSeverity, sev_name, SignalSeverity.WARNING)
        emit_scout_signal(
            SignalCategory.GOVERNANCE if hasattr(SignalCategory, "GOVERNANCE") else SignalCategory.ANOMALY,
            severity,
            action,
            f"channel:{envelope.channel}:msg:{message_id or envelope.external_message_id}",
            details,
            correlation_id=correlation,
            threat_score=threat,
        )
    except Exception:
        return None
    return correlation


def honour_scout_command(command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply local Scout control commands relevant to Channel Shield."""
    cfg = load_channel_shield_config()
    if not cfg.scout_honour_commands:
        return {"honoured": False, "reason": "scout honour disabled"}
    payload = payload or {}
    cmd = (command or "").strip().lower()
    if cmd in {"suspend", "quarantine", "set_sandbox", "set-sandbox"}:
        return {"honoured": True, "command": cmd, "payload": payload, "local": True}
    return {"honoured": False, "reason": f"unsupported command: {command}"}

"""Incident response orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.governance.kill_relay import apply_kill_directive
from keprix.incident.severity import IncidentLevel, SEVERITY_MATRIX
from keprix.incident.store import append_timeline, create_incident, get_incident
from keprix.security.scout_control import (
    block_session,
    quarantine_tool,
    set_egress_force_blocked,
)
from keprix.security.scout_integration import emit_scout_signal
from keprix.security.scout_types import SignalCategory, SignalSeverity


_VAULT_SEAL_PATH = Path.home() / ".keprix" / "security" / "vault_sealed.json"


def is_vault_sealed() -> bool:
    if not _VAULT_SEAL_PATH.exists():
        return False
    try:
        payload = json.loads(_VAULT_SEAL_PATH.read_text(encoding="utf-8"))
        return bool(payload.get("sealed"))
    except Exception:
        return False


def seal_vault(*, reason: str = "incident_response") -> dict[str, Any]:
    _VAULT_SEAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    payload = {
        "sealed": True,
        "reason": reason,
        "sealed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _VAULT_SEAL_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.CRITICAL,
        "vault.sealed",
        "vault:credentials",
        payload,
    )
    return payload


def unseal_vault() -> dict[str, Any]:
    if _VAULT_SEAL_PATH.exists():
        _VAULT_SEAL_PATH.unlink()
    return {"sealed": False}


def rotate_credentials(*, product_id: str = "all") -> dict[str, Any]:
    """Signal credential rotation for proxy-managed secrets."""
    from keprix.proxy.rotation import write_rotation_signal

    refs = ["provider:openai", "provider:anthropic", "scout:api_key"]
    rotated: list[dict[str, Any]] = []
    for ref in refs:
        try:
            rotated.append(write_rotation_signal(ref, verify=False))
        except Exception as exc:
            rotated.append({"secret_ref": ref, "ok": False, "error": str(exc)})
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.CRITICAL,
        "credentials.rotation_requested",
        f"product:{product_id}",
        {"product_id": product_id, "refs": refs},
    )
    return {"product_id": product_id, "rotation_signals": rotated}


def lockdown_product(product_id: str, *, reason: str = "incident_lockdown") -> dict[str, Any]:
    actions: list[str] = []
    set_egress_force_blocked(True)
    actions.append("egress_blocked")
    seal_vault(reason=reason)
    actions.append("vault_sealed")
    apply_kill_directive("stop_agent", {"product_id": product_id, "reason": reason})
    actions.append("instance_suspended")
    from keprix.security.product_policy import apply_product_policy

    apply_product_policy(
        product_id,
        {
            "security_profile": "maximum",
            "sandbox": {"mode": "session_only"},
            "tools": {"quarantined_tools": ["shell-exec", "code-exec", "file-write"]},
        },
        updated_by="incident_response",
    )
    actions.append("policy_hardened")
    return {"product_id": product_id, "actions": actions}


def declare_incident(
    *,
    level: IncidentLevel,
    reason: str,
    product_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    actions: list[str] = []
    if level == IncidentLevel.L2_WARNING:
        tool = "shell-exec"
        quarantine_tool(tool)
        actions.append(f"quarantined:{tool}")
    elif level == IncidentLevel.L3_CRITICAL:
        if session_id:
            block_session(session_id)
            actions.append(f"blocked_session:{session_id}")
        from keprix.forensics.snapshot import capture_snapshot

        snapshot = capture_snapshot(session_id=session_id, reason=reason)
        actions.append(f"snapshot:{snapshot.get('id')}")
    elif level == IncidentLevel.L4_EMERGENCY:
        apply_kill_directive("stop_agent", {"reason": reason, "permanent": False})
        actions.append("instance_suspended")
        set_egress_force_blocked(True)
        actions.append("egress_blocked")
        seal_vault(reason=reason)
        actions.append("vault_sealed")
        rotate_credentials(product_id=product_id or "all")
        actions.append("credentials_rotation_requested")
        from keprix.forensics.snapshot import capture_snapshot

        snapshot = capture_snapshot(session_id=session_id, reason=reason)
        actions.append(f"snapshot:{snapshot.get('id')}")

    record = create_incident(
        level=level,
        reason=reason,
        product_id=product_id,
        session_id=session_id,
        actions=actions,
    )
    spec = SEVERITY_MATRIX[level]
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.CRITICAL if level.value in {"critical", "emergency"} else SignalSeverity.WARNING,
        "incident.declared",
        f"incident:{record['id']}",
        {
            "incident_id": record["id"],
            "level": level.value,
            "reason": reason,
            "auto_response": spec.auto_response,
            "actions": actions,
        },
        product_id=product_id,
    )
    return {"incident": record, "actions": actions, "severity": spec.name}


def post_mortem_template_path() -> Path:
    return Path(__file__).resolve().parent / "templates" / "post_mortem.md"


def render_post_mortem(incident_id: str) -> str:
    incident = get_incident(incident_id)
    if incident is None:
        raise KeyError(incident_id)
    template = post_mortem_template_path().read_text(encoding="utf-8")
    timeline = "\n".join(
        f"- {row.get('at')}: {row.get('event')} {row.get('detail', '')}".rstrip()
        for row in incident.get("timeline") or []
    )
    return (
        template.replace("{{incident_id}}", incident_id)
        .replace("{{level}}", str(incident.get("level")))
        .replace("{{reason}}", str(incident.get("reason")))
        .replace("{{opened_at}}", str(incident.get("opened_at")))
        .replace("{{timeline}}", timeline or "- (none recorded)")
    )


def note_incident_event(incident_id: str, event: str, detail: str = "") -> dict[str, Any] | None:
    return append_timeline(incident_id, event, detail)

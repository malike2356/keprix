"""Bridge between SCOUT persona and local policy / optional Scout connector."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from keprix.compat import UTC, StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.extensions.scout.persona.persona import SCOUT_PERSONA
from keprix.governance.client import get_governance_client
from keprix.governance.event_reporter import queue_audit_event
from keprix.governance.kill_relay import (
    apply_kill_directive,
    clear_kill_state,
    get_kill_state,
    tools_disabled,
    workspace_locked,
)
from keprix.governance.policy_receiver import get_policy_registry
from keprix.governance.signing import sign_payload
from keprix.governance.store import get_governance_store

ALERT_CHANNELS = ("email", "slack", "teams", "sms", "webhook", "pagerduty")

COMPLIANCE_TEMPLATES: dict[str, list[str]] = {
    "gdpr": [
        "Records of processing activities",
        "Lawful basis documentation",
        "Data subject rights procedure",
        "Breach notification runbook (72-hour ICO consideration)",
        "Processor agreement inventory",
    ],
    "iso_27001": [
        "Information security policy",
        "Risk treatment plan",
        "Access control matrix",
        "Incident response records",
        "Supplier security assessments",
    ],
    "pci_dss": [
        "Cardholder data environment scope",
        "Network segmentation evidence",
        "Access logging and review",
        "Vulnerability management records",
        "Quarterly scan attestations",
    ],
}


class KillLevel(StrEnum):
    PLATFORM = "platform"
    ENGAGEMENT = "engagement"
    TOOL = "tool"


_KILL_DIRECTIVE_MAP = {
    KillLevel.PLATFORM: "stop_agent",
    KillLevel.ENGAGEMENT: "lock_workspace",
    KillLevel.TOOL: "disable_tools",
}


def _scout_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "scout"
    except Exception:
        root = Path.home() / ".keprix" / "scout"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _local_kill_path() -> Path:
    return _scout_dir() / "local_kill.json"


def read_local_kill_state() -> dict[str, Any]:
    path = _local_kill_path()
    if not path.exists():
        return {"active": False, "levels": [], "reason": "", "updated_at": None}
    return json.loads(path.read_text(encoding="utf-8"))


def write_local_kill_state(*, active: bool, levels: list[str], reason: str) -> dict[str, Any]:
    payload = {
        "active": active,
        "levels": levels,
        "reason": reason,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _local_kill_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def apply_local_kill_levels(levels: list[str], *, reason: str) -> dict[str, Any]:
    for level in levels:
        directive = _KILL_DIRECTIVE_MAP.get(KillLevel(level))
        if directive:
            apply_kill_directive(directive, {"reason": reason, "source": "local"})
    return write_local_kill_state(active=True, levels=levels, reason=reason)


def clear_local_kill_state() -> None:
    path = _local_kill_path()
    if path.exists():
        path.unlink()
    clear_kill_state()


@dataclass(slots=True)
class PolicyCheckpointResult:
    allowed: bool
    reason: str
    tool_name: str
    persona: str
    kill_active: bool = False
    policy_violation: bool = False
    overridden_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "tool_name": self.tool_name,
            "persona": self.persona,
            "kill_active": self.kill_active,
            "policy_violation": self.policy_violation,
            "overridden_by": self.overridden_by,
        }


@dataclass
class EvidencePack:
    pack_id: str
    created_at: str
    events: list[dict[str, Any]]
    integrity_hash: str
    signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "created_at": self.created_at,
            "events": list(self.events),
            "integrity_hash": self.integrity_hash,
            "signature": self.signature,
        }


class GovernancePolicyBridge:
    """Keprix-side governance shell; optional paid Scout connector sits behind this."""

    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = SCOUT_PERSONA

    def _sync_local_kill_into_relay(self) -> dict[str, Any]:
        local = read_local_kill_state()
        if local.get("active"):
            for level in local.get("levels", []):
                try:
                    directive = _KILL_DIRECTIVE_MAP[KillLevel(level)]
                except ValueError:
                    continue
                apply_kill_directive(directive, {"reason": local.get("reason", ""), "source": "local_persisted"})
        return local

    async def governance_status(self) -> dict[str, Any]:
        local = self._sync_local_kill_into_relay()
        client = get_governance_client()
        connector = await client.status()
        return {
            "persona": self.persona.name,
            "workspace_id": self.workspace_id,
            "connector_configured": bool(connector.get("connected")),
            "connector_enabled": bool(connector.get("enabled")),
            "policy_snapshot": connector.get("policy_snapshot", get_policy_registry().snapshot()),
            "kill_state": connector.get("kill_state", get_kill_state().to_dict()),
            "local_kill": local,
            "alert_channels": list(ALERT_CHANNELS),
            "scout_url": connector.get("scout_url"),
        }

    def evaluate_tool_execution(self, tool_name: str, *, persona: str = "FORGE") -> PolicyCheckpointResult:
        if persona.upper() == "SCOUT":
            return PolicyCheckpointResult(
                allowed=True,
                reason="SCOUT governance checkpoints are authoritative.",
                tool_name=tool_name,
                persona=persona,
            )

        local = self._sync_local_kill_into_relay()
        kill = get_kill_state()
        registry = get_policy_registry()

        if local.get("active") or kill.stop_agent:
            return PolicyCheckpointResult(
                allowed=False,
                reason="Policy prohibits this action. Platform kill switch is active.",
                tool_name=tool_name,
                persona=persona,
                kill_active=True,
            )
        if kill.lock_workspace or KillLevel.ENGAGEMENT.value in local.get("levels", []):
            return PolicyCheckpointResult(
                allowed=False,
                reason="Policy prohibits this action. Engagement is locked.",
                tool_name=tool_name,
                persona=persona,
                kill_active=True,
            )
        if tools_disabled():
            return PolicyCheckpointResult(
                allowed=False,
                reason="Policy prohibits this action. Tool execution is disabled.",
                tool_name=tool_name,
                persona=persona,
                kill_active=True,
            )
        if registry.is_tool_blocked(tool_name):
            return PolicyCheckpointResult(
                allowed=False,
                reason=f"Policy prohibits this action. Tool '{tool_name}' is blocked by active policy.",
                tool_name=tool_name,
                persona=persona,
                policy_violation=True,
            )

        return PolicyCheckpointResult(
            allowed=True,
            reason="Policy checkpoint passed.",
            tool_name=tool_name,
            persona=persona,
        )

    def activate_kill_switch(
        self,
        level: str,
        *,
        reason: str = "Manual kill switch activation",
        propagate_scheduler: bool = True,
    ) -> dict[str, Any]:
        normalized = KillLevel(level)
        directive = _KILL_DIRECTIVE_MAP[normalized]
        apply_kill_directive(directive, {"reason": reason, "activated_by": "SCOUT"})
        local = read_local_kill_state()
        levels = list(dict.fromkeys([*local.get("levels", []), normalized.value]))
        local_state = write_local_kill_state(active=True, levels=levels, reason=reason)
        scheduler = (
            self.propagate_kill_to_scheduler(reason=reason)
            if propagate_scheduler and normalized == KillLevel.PLATFORM
            else {"paused_jobs": 0}
        )
        return {
            "level": normalized.value,
            "directive": directive,
            "local_kill": local_state,
            "kill_state": get_kill_state().to_dict(),
            "scheduler": scheduler,
        }

    def clear_kill_switch(self, *, clear_scheduler: bool = False) -> dict[str, Any]:
        clear_local_kill_state()
        scheduler = self.resume_scheduler_jobs() if clear_scheduler else {"resumed_jobs": 0}
        return {"cleared": True, "kill_state": get_kill_state().to_dict(), "scheduler": scheduler}

    def propagate_kill_to_scheduler(self, *, reason: str = "SCOUT platform kill switch") -> dict[str, Any]:
        from keprix.cron.jobs import load_jobs, pause_job

        paused: list[str] = []
        for job in load_jobs():
            if job.get("enabled", True) and job.get("state") != "paused":
                updated = pause_job(str(job.get("id") or job.get("name") or ""), reason=reason)
                if updated:
                    paused.append(str(updated.get("id") or updated.get("name") or ""))
        return {"paused_jobs": len(paused), "job_ids": paused}

    def resume_scheduler_jobs(self) -> dict[str, Any]:
        from keprix.cron.jobs import load_jobs, resume_job

        resumed: list[str] = []
        for job in load_jobs():
            if not job.get("enabled", True) or job.get("state") == "paused":
                updated = resume_job(str(job.get("id") or job.get("name") or ""))
                if updated:
                    resumed.append(str(updated.get("id") or updated.get("name") or ""))
        return {"resumed_jobs": len(resumed), "job_ids": resumed}

    async def stream_audit_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        enriched = {
            **payload,
            "workspace_id": self.workspace_id,
            "governed_by": "SCOUT",
            "streamed_at": datetime.now(UTC).isoformat(),
        }
        await queue_audit_event(event_type, enriched)
        row = await get_governance_store().enqueue_event(event_type, enriched)
        return {"queued": True, "event": row}

    async def build_evidence_pack(self, *, limit: int = 25, secret: str = "scout-evidence-local") -> EvidencePack:
        events = await get_governance_store().list_recent_events(limit=limit)
        canonical = json.dumps(events, sort_keys=True, separators=(",", ":"))
        integrity_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        signature = sign_payload(secret, canonical.encode("utf-8"))
        return EvidencePack(
            pack_id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            events=events,
            integrity_hash=integrity_hash,
            signature=signature,
        )

    def compliance_export_template(self, framework: str) -> dict[str, Any]:
        key = framework.lower().replace("-", "_")
        items = COMPLIANCE_TEMPLATES.get(key)
        if items is None:
            return {
                "framework": framework,
                "supported": False,
                "items": [],
                "message": "Template not available. Configure Scout connector for enterprise exports.",
            }
        return {
            "framework": framework,
            "supported": True,
            "items": items,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def route_violation_to_nexus(self, violation: PolicyCheckpointResult) -> dict[str, Any]:
        return {
            "escalate_to": "NEXUS",
            "from_persona": "SCOUT",
            "reason": violation.reason,
            "tool_name": violation.tool_name,
            "persona": violation.persona,
            "policy_violation": violation.policy_violation,
            "kill_active": violation.kill_active,
            "message": (
                f"SCOUT policy violation on tool '{violation.tool_name}' "
                f"(requested by {violation.persona}). {violation.reason}"
            ),
        }

    def handoff_to_codex(self, evidence_pack: EvidencePack) -> dict[str, Any]:
        return {
            "target_persona": "CODEX",
            "pack_id": evidence_pack.pack_id,
            "integrity_hash": evidence_pack.integrity_hash,
            "event_count": len(evidence_pack.events),
            "message": "Evidence pack ready for CODEX legal review.",
        }

    async def connector_handoff(self, action: str) -> dict[str, Any]:
        status = await self.governance_status()
        if not status.get("connector_configured"):
            return {
                "ok": False,
                "action": action,
                "message": "Labyrinth Scout connector is not configured. Local policy controls remain active.",
            }
        client = get_governance_client()
        if action == "heartbeat":
            result = await client.heartbeat(user_id=self.user_id)
            return {"ok": True, "action": action, "result": result}
        if action == "flush_events":
            result = await client.flush_events(user_id=self.user_id)
            return {"ok": True, "action": action, "result": result}
        return {"ok": True, "action": action, "status": status}

    def cannot_be_overridden(self, requesting_persona: str) -> bool:
        return requesting_persona.upper() != "SCOUT"

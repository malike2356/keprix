"""Tests for SCOUT governance persona (scout extension)."""

from __future__ import annotations

import pytest

from keprix.extensions.scout.persona.persona import SCOUT_PERSONA
from keprix.extensions.scout.persona.policy_bridge import (
    GovernancePolicyBridge,
    KillLevel,
    clear_local_kill_state,
    read_local_kill_state,
)
from keprix.governance.kill_relay import clear_kill_state, get_kill_state
from keprix.governance.policy_receiver import get_policy_registry
from keprix.governance.signing import sign_payload
from keprix.governance.store import GovernanceStore


@pytest.fixture(autouse=True)
def reset_governance_state() -> None:
    clear_kill_state()
    clear_local_kill_state()
    get_policy_registry().reload_from_store([])
    yield
    clear_kill_state()
    clear_local_kill_state()
    get_policy_registry().reload_from_store([])


@pytest.fixture
def bridge(tmp_path, monkeypatch) -> GovernancePolicyBridge:
    store = GovernanceStore(base_dir=tmp_path / "governance")
    monkeypatch.setattr("keprix.governance.store.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.event_reporter.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.extensions.scout.persona.policy_bridge.get_governance_store", lambda: store)
    monkeypatch.setattr(
        "keprix.extensions.scout.persona.policy_bridge._local_kill_path",
        lambda: tmp_path / "local_kill.json",
    )
    return GovernancePolicyBridge(workspace_id="ws-governance", user_id="user-governance")


def test_scout_persona_identity() -> None:
    assert SCOUT_PERSONA.name == "SCOUT"
    assert SCOUT_PERSONA.colour == "#6B7280"
    assert SCOUT_PERSONA.agent_type == "governance"
    prompt = SCOUT_PERSONA.system_prompt()
    assert "SCOUT" in prompt
    assert "governance" in prompt.lower()


def test_checkpoint_allows_when_policy_clear(bridge: GovernancePolicyBridge) -> None:
    result = bridge.evaluate_tool_execution("deploy_tool", persona="FORGE")
    assert result.allowed is True
    assert result.reason == "Policy checkpoint passed."


def test_checkpoint_blocks_on_platform_kill(bridge: GovernancePolicyBridge) -> None:
    bridge.activate_kill_switch(KillLevel.PLATFORM, reason="test platform kill")
    result = bridge.evaluate_tool_execution("deploy_tool", persona="FORGE")
    assert result.allowed is False
    assert result.kill_active is True
    assert "Platform kill switch" in result.reason


def test_local_kill_persists_without_connector(bridge: GovernancePolicyBridge, tmp_path, monkeypatch) -> None:
    bridge.activate_kill_switch(KillLevel.PLATFORM, reason="offline kill", propagate_scheduler=False)
    local = read_local_kill_state()
    assert local["active"] is True
    assert KillLevel.PLATFORM.value in local["levels"]

    clear_kill_state()
    restored = bridge.evaluate_tool_execution("deploy_tool", persona="FORGE")
    assert restored.allowed is False
    assert get_kill_state().stop_agent is True


def test_scout_cannot_be_overridden(bridge: GovernancePolicyBridge) -> None:
    bridge.activate_kill_switch(KillLevel.PLATFORM, propagate_scheduler=False)
    assert bridge.cannot_be_overridden("FORGE") is True
    assert bridge.cannot_be_overridden("SCOUT") is False


def test_policy_blocked_tool(bridge: GovernancePolicyBridge) -> None:
    registry = get_policy_registry()
    registry.reload_from_store(
        [
            {
                "policy_type": "tool_block",
                "policy_value": {"tool_name": "shell_exec"},
                "active": True,
            }
        ]
    )
    result = bridge.evaluate_tool_execution("shell_exec", persona="FORGE")
    assert result.allowed is False
    assert result.policy_violation is True


def test_nexus_violation_routing(bridge: GovernancePolicyBridge) -> None:
    bridge.evaluate_tool_execution("shell_exec", persona="FORGE")
    bridge.activate_kill_switch(KillLevel.TOOL, propagate_scheduler=False)
    blocked = bridge.evaluate_tool_execution("deploy_tool", persona="FORGE")
    escalation = bridge.route_violation_to_nexus(blocked)
    assert escalation["escalate_to"] == "NEXUS"
    assert escalation["from_persona"] == "SCOUT"
    assert blocked.tool_name in escalation["message"]


@pytest.mark.asyncio
async def test_audit_stream_and_evidence_pack(bridge: GovernancePolicyBridge) -> None:
    await bridge.stream_audit_event("tool.execution", {"tool": "deploy_tool", "ok": True})
    pack = await bridge.build_evidence_pack(limit=5, secret="test-secret")
    assert pack.pack_id
    assert pack.integrity_hash
    canonical = __import__("json").dumps(pack.events, sort_keys=True, separators=(",", ":"))
    assert pack.signature == sign_payload("test-secret", canonical.encode("utf-8"))


def test_compliance_export_templates(bridge: GovernancePolicyBridge) -> None:
    gdpr = bridge.compliance_export_template("gdpr")
    assert gdpr["supported"] is True
    assert len(gdpr["items"]) >= 3
    unknown = bridge.compliance_export_template("soc2")
    assert unknown["supported"] is False


@pytest.mark.asyncio
async def test_governance_status_without_connector(bridge: GovernancePolicyBridge) -> None:
    status = await bridge.governance_status()
    assert status["persona"] == "SCOUT"
    assert status["connector_configured"] is False
    assert "email" in status["alert_channels"]


@pytest.mark.asyncio
async def test_connector_handoff_when_unconfigured(bridge: GovernancePolicyBridge) -> None:
    result = await bridge.connector_handoff("heartbeat")
    assert result["ok"] is False
    assert "not configured" in result["message"].lower()


def test_kill_switch_propagates_to_scheduler(bridge: GovernancePolicyBridge, monkeypatch) -> None:
    paused: list[str] = []

    def fake_pause(job_id: str, reason: str | None = None):
        paused.append(job_id)
        return {"id": job_id, "state": "paused", "enabled": False}

    monkeypatch.setattr("keprix.cron.jobs.load_jobs", lambda: [{"id": "job-1", "enabled": True, "state": "active"}])
    monkeypatch.setattr("keprix.cron.jobs.pause_job", fake_pause)

    result = bridge.activate_kill_switch(KillLevel.PLATFORM, reason="scheduler test")
    assert result["scheduler"]["paused_jobs"] == 1
    assert paused == ["job-1"]

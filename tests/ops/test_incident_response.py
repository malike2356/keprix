"""Tests for incident response, operations runbook, and forensics."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from keprix.forensics.chain import verify_chain
from keprix.forensics.snapshot import capture_snapshot, list_snapshots
from keprix.governance.kill_relay import agent_stop_requested, clear_kill_state
from keprix.incident.response import declare_incident, is_vault_sealed, seal_vault
from keprix.incident.severity import IncidentLevel
from keprix.incident.store import list_incidents
from keprix.ops.drill import run_drill
from keprix.ops.reports import report_24h
from keprix.ops.runbook import RunbookExecutor
from keprix.security.auto_response import evaluate_signal, reset_auto_response_state
from keprix.security.credential_vault_audit import audit_credentials
from keprix.security.pentest import run_pentest
from keprix.security.scout_control import reset_scout_control


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_scout_control()
    reset_auto_response_state()
    clear_kill_state()
    yield
    reset_scout_control()
    reset_auto_response_state()
    clear_kill_state()


def test_declare_l3_incident_creates_record_and_snapshot():
    result = declare_incident(
        level=IncidentLevel.L3_CRITICAL,
        reason="injection_campaign",
        product_id="petraclus",
        session_id="sess-1",
    )
    assert result["incident"]["id"].startswith("inc-")
    assert any("snapshot:" in action for action in result["actions"])
    assert list_incidents()


def test_declare_l4_incident_triggers_lockdown_actions():
    result = declare_incident(
        level=IncidentLevel.L4_EMERGENCY,
        reason="credential_exfiltration",
        product_id="abbis",
    )
    assert agent_stop_requested() is True
    assert is_vault_sealed() is True
    assert "vault_sealed" in result["actions"]


def test_forensic_snapshot_and_chain_verify(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    payload = capture_snapshot(session_id="sess-9", reason="test")
    assert payload["id"].startswith("ckpt-")
    chain = verify_chain()
    assert chain["ok"] is True
    assert list_snapshots()


def test_auto_response_triggers_l3_after_threshold():
    response = None
    for _ in range(3):
        response = evaluate_signal(
            session_id="sess-auto",
            product_id="fleet_z",
            severity="critical",
            action="injection_detected",
        )
    assert response is not None
    assert response["severity"] == "CRITICAL"


def test_pentest_quick_passes_baseline():
    payload = run_pentest(full=False)
    assert payload["total"] >= 3
    assert "checks" in payload


def test_credential_vault_audit_returns_rows():
    payload = audit_credentials(expiring_days=7)
    assert "credentials" in payload
    assert "issue_count" in payload


def test_report_24h_payload():
    payload = report_24h()
    assert payload["period"] == "24h"
    assert "signals_24h" in payload


@pytest.mark.asyncio
async def test_daily_runbook_executes_checks():
    executor = RunbookExecutor()
    with patch.object(executor, "_upstream_check", new_callable=AsyncMock) as upstream:
        upstream.return_value = executor._credential_expiry()
        checks = await executor.daily()
    assert len(checks) >= 5
    assert all(hasattr(check, "passed") for check in checks)


def test_incident_drill_completes_quickly():
    payload = run_drill(level="l3")
    assert payload["ok"] is True
    assert payload["elapsed_seconds"] <= payload["target_seconds"]


def test_seal_vault_persists_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    payload = seal_vault(reason="test")
    assert payload["sealed"] is True
    assert is_vault_sealed() is True

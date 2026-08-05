"""Tests for multi-product Scout dashboard, policies, and correlation."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from keprix.governance.policy_receiver import get_policy_registry
from keprix.security.product_policy import apply_product_policy, get_policy, list_policies
from keprix.security.scout_alerts import ScoutAlertConfig
from keprix.security.scout_config import ScoutConfig
from keprix.security.scout_correlation import append_signal_event, correlate_attacks, dashboard_summary
from keprix.security.scout_integration import emit_scout_signal
from keprix.security.scout_listener import ScoutListener
from keprix.security.scout_metrics import product_metrics, record_signal, reset_metrics
from keprix.security.scout_registration import ScoutRegistration
from keprix.security.scout_types import ScoutCommand, SignalCategory, SignalSeverity


@pytest.fixture(autouse=True)
def _reset_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_metrics()
    get_policy_registry().reload_from_store([])
    yield
    reset_metrics()


@pytest.mark.asyncio
async def test_register_all_enabled_products_persists_local(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reg = ScoutRegistration()
    with patch.object(reg, "_post_registration", new_callable=AsyncMock):
        rows = await reg.register_all_enabled_products()
    assert rows
    local = reg.list_local_registrations()
    assert len(local) >= 1
    assert local[0].get("product_id")


@pytest.mark.asyncio
async def test_deregister_removes_local_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reg = ScoutRegistration()
    with patch.object(reg, "_post_registration", new_callable=AsyncMock):
        await reg.register_manifest(
            product_id="petraclus",
            product_name="Petraclus",
            product_version="1.0.0",
            features={},
        )
    assert len(reg.list_local_registrations()) == 1
    await reg.deregister("petraclus")
    assert reg.list_local_registrations() == []


def test_emit_scout_signal_records_metrics_and_correlation():
    emit_scout_signal(
        SignalCategory.PROMPT_INJECTION,
        SignalSeverity.WARNING,
        "injection_detected",
        "source:test",
        {"patterns_matched": ["ignore_instructions"]},
        product_id="abbis",
        threat_score=0.8,
    )
    metrics = product_metrics("abbis")
    assert metrics.get("signals_total", 0) >= 1
    attacks = correlate_attacks()
    assert isinstance(attacks, list)


def test_dashboard_summary_includes_registered_agents(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reg_path = tmp_path / ".keprix" / "scout" / "registrations.json"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(
        json.dumps(
            {
                "agents": {
                    "abbis": {
                        "product_id": "abbis",
                        "product_name": "AbbiS",
                        "product_version": "1.2.0",
                        "security_profile": "maximum",
                        "status": "online",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    record_signal("abbis", severity="warning", action="test")
    summary = dashboard_summary()
    assert summary["agent_count"] == 1
    assert summary["agents"][0]["product_id"] == "abbis"
    assert summary["agents"][0]["signals_24h"] >= 1


def test_apply_product_policy_persists_and_enforces_tools():
    record = apply_product_policy(
        "petraclus",
        {
            "security_profile": "high",
            "tools": {"quarantined_tools": ["shell-exec"]},
            "egress": {"allowed_domains": ["api.openai.com:443"]},
        },
        updated_by="test",
    )
    assert record["version"] == 1
    assert get_policy("petraclus")["security_profile"] == "high"
    assert get_policy_registry().is_tool_blocked("shell-exec") is True
    policies = list_policies()
    assert "petraclus" in policies


def test_correlate_attacks_groups_cross_product_events(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    for product in ("abbis", "petraclus", "fleet_z"):
        append_signal_event(
            {
                "product": product,
                "category": "prompt_injection",
                "severity": "critical",
                "action": "injection_detected",
                "target": "source:web",
                "threat_score": 0.9,
                "details": {"patterns_matched": ["ignore_instructions"]},
            }
        )
    attacks = correlate_attacks()
    assert attacks
    assert len(attacks[0]["products_hit"]) >= 2


def test_scout_alert_config_per_product(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = ScoutAlertConfig()
    record = cfg.configure_product_alerts(
        "abbis",
        {
            "alert_channels": [{"type": "email", "address": "security@example.test", "min_severity": "critical"}],
            "quiet_hours": {"start": 23, "end": 6},
        },
    )
    assert record["alert_channels"]
    assert cfg.get_product_alerts("abbis")["quiet_hours"]["start"] == 23


@pytest.mark.asyncio
async def test_set_sandbox_policy_command_applies_product_policy():
    listener = ScoutListener(
        ScoutConfig(
            enabled=True,
            api_key="key",
            endpoint="https://scout.example.test",
            redis_url="redis://localhost:6379/0",
            agent_id="instance-test",
            product="keprix",
        )
    )
    await listener.handle_message(
        json.dumps(
            {
                "command_id": "cmd-sandbox",
                "command": ScoutCommand.SET_SANDBOX_POLICY.value,
                "agent_id": "*",
                "params": {
                    "product": "petraclus",
                    "policy": {
                        "security_profile": "high",
                        "sandbox": {"mode": "docker", "max_runtime_seconds": 300},
                    },
                },
                "issued_by": "scout",
                "issued_at": "2026-07-10T00:00:00+00:00",
            }
        )
    )
    policy = get_policy("petraclus")
    assert policy is not None
    assert policy["sandbox"]["mode"] == "docker"


@pytest.mark.asyncio
async def test_set_tool_policy_command_with_full_policy():
    listener = ScoutListener(
        ScoutConfig(
            enabled=True,
            api_key="key",
            endpoint="https://scout.example.test",
            redis_url="redis://localhost:6379/0",
            agent_id="instance-test",
            product="keprix",
        )
    )
    await listener.handle_message(
        json.dumps(
            {
                "command_id": "cmd-tool-policy",
                "command": ScoutCommand.SET_TOOL_POLICY.value,
                "agent_id": "*",
                "params": {
                    "product_id": "fleet_z",
                    "policy": {
                        "tools": {"quarantined_tools": ["code-exec"]},
                    },
                },
                "issued_by": "scout",
                "issued_at": "2026-07-10T00:00:00+00:00",
            }
        )
    )
    assert get_policy("fleet_z") is not None
    assert get_policy_registry().is_tool_blocked("code-exec") is True


def test_scout_dashboard_routes_require_admin():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from keprix.api.auth import require_admin
    from keprix.api.scout_dashboard_routes import router as scout_dashboard_router

    app = FastAPI()
    app.include_router(scout_dashboard_router)
    client = TestClient(app)
    response = client.get("/api/v1/scout/dashboard/summary")
    assert response.status_code in {401, 403}

    app.dependency_overrides[require_admin] = lambda: "admin"
    try:
        response = client.get("/api/v1/scout/dashboard/summary")
        assert response.status_code == 200
        body = response.json()
        assert "agents" in body
    finally:
        app.dependency_overrides.clear()

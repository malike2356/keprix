"""Tests for Prompt 16: Self-Configuration."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from keprix.agents.self_config_agent import handle_self_config_request, is_self_config_request
from keprix.brain.llm_router import LLMRouter
from keprix.config.auto_repair import _repair_redis, handle_health_change
from keprix.config.env_discovery import discover_environment
from keprix.config.health_monitor import ComponentHealth, ConfigHealthMonitor
from keprix.config.optimizer import apply_proposal, run_optimizer
from keprix.config.paths import generated_env_file, overrides_env_file, proposals_file
from keprix.config.telemetry import JsonlTelemetryStore
from keprix.db.memory_fallback import activate_memory_fallback, is_memory_fallback_active, reset_memory_fallback


@pytest.fixture
def self_config_home(tmp_path, monkeypatch):
    data_dir = tmp_path / "self-config"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("keprix.config.paths.get_data_dir", lambda: data_dir)
    monkeypatch.setattr(
        "keprix.config.env_discovery.generated_env_file",
        lambda: data_dir / "generated.env",
    )
    monkeypatch.setattr("keprix.config.optimizer.proposals_file", lambda: data_dir / "config_proposals.jsonl")
    monkeypatch.setattr("keprix.config.optimizer.overrides_env_file", lambda: data_dir / "overrides.env")
    monkeypatch.setattr("keprix.config.optimizer.rollback_file", lambda: data_dir / "env_rollback.jsonl")
    return data_dir


@pytest.mark.asyncio
async def test_discover_environment_writes_generated_env(self_config_home, monkeypatch):
    monkeypatch.delenv("KEPRIX_REDIS_PASSWORD", raising=False)
    config = await discover_environment()
    out = generated_env_file()
    assert out.exists()
    assert "KEPRIX_API_PORT" in config
    assert "KEPRIX_REDIS_PASSWORD" in config
    content = out.read_text()
    assert "KEPRIX_API_PORT=" in content
    assert "KEPRIX_REDIS_PASSWORD=" in content


@pytest.mark.asyncio
async def test_health_monitor_records_component(monkeypatch):
    monitor = ConfigHealthMonitor()

    async def fake_egress():
        return [
            ComponentHealth(
                name="egress:api.openai.com",
                status="healthy",
                latency_ms=12.0,
                error="",
                checked_at=1.0,
            )
        ]

    monkeypatch.setattr(monitor, "_check_llm_providers", AsyncMock(return_value=[]))
    monkeypatch.setattr(monitor, "_check_redis", AsyncMock(return_value=[]))
    monkeypatch.setattr(monitor, "_check_postgres", AsyncMock(return_value=[]))
    monkeypatch.setattr(monitor, "_check_channel_adapters", AsyncMock(return_value=[]))
    monkeypatch.setattr(monitor, "_check_egress", fake_egress)

    await monitor._run_all_checks()
    assert "egress:api.openai.com" in monitor.get_all()


@pytest.mark.asyncio
async def test_llm_provider_demoted_on_failure(monkeypatch):
    LLMRouter.reset_instance()
    router = LLMRouter.get_instance()
    demoted: list[str] = []

    def fake_demote(provider_name: str, reason: str = "") -> None:
        demoted.append(provider_name)

    monkeypatch.setattr(router, "demote_provider", fake_demote)
    events: list[tuple[str, str, dict]] = []

    async def capture(event_type, severity, detail):
        events.append((event_type, severity, detail))

    monkeypatch.setattr("keprix.config.auto_repair.report_security_event", capture)

    health = ComponentHealth(
        name="llm:deepseek",
        status="down",
        latency_ms=0,
        error="HTTP 503",
        checked_at=1.0,
    )
    await handle_health_change(health)
    assert demoted == ["deepseek"]
    assert events[0][0] == "config_auto_repair"
    assert events[0][2]["action"] == "llm_provider_demoted"


@pytest.mark.asyncio
async def test_redis_fallback_activates_after_reconnect_failure(monkeypatch):
    reset_memory_fallback()
    monkeypatch.setattr(
        "keprix.db.redis_client.reconnect_redis",
        AsyncMock(side_effect=RuntimeError("down")),
    )
    events: list[tuple[str, str, dict]] = []

    async def capture(event_type, severity, detail):
        events.append((event_type, severity, detail))

    monkeypatch.setattr("keprix.config.auto_repair.report_security_event", capture)
    monkeypatch.setattr("keprix.config.auto_repair.asyncio.sleep", AsyncMock())

    await _repair_redis("connection refused")
    assert is_memory_fallback_active()
    assert any(event[2].get("action") == "redis_fallback_activated" for event in events)
    reset_memory_fallback()


@pytest.mark.asyncio
async def test_optimizer_creates_proposal_for_high_error_rate(self_config_home):
    telemetry_path = self_config_home / "telemetry.jsonl"
    telemetry_path.write_text(
        json.dumps(
            {
                "kind": "provider",
                "provider": "deepseek",
                "error_rate": 0.2,
                "call_count": 150,
                "error_count": 30,
                "next_best_provider": "groq",
            }
        )
        + "\n"
    )
    store = JsonlTelemetryStore(telemetry_path)
    proposals = await run_optimizer(store)
    assert proposals
    pending_path = proposals_file()
    assert pending_path.exists()
    rows = [json.loads(line) for line in pending_path.read_text().splitlines() if line.strip()]
    assert any(row["category"] == "llm_routing" for row in rows)


@pytest.mark.asyncio
async def test_apply_proposal_writes_overrides_env(self_config_home, monkeypatch):
    proposal = {
        "proposal_id": "llm-swap-test",
        "category": "llm_routing",
        "description": "test",
        "current_value": "deepseek",
        "proposed_value": "groq",
        "rationale": "test",
        "env_key": "KEPRIX_DEFAULT_LLM_PROVIDER",
        "risk": "low",
        "created_at": 1.0,
        "status": "pending",
    }
    proposals_file().write_text(json.dumps(proposal) + "\n")
    events: list[tuple[str, str, dict]] = []

    async def capture(event_type, severity, detail):
        events.append((event_type, severity, detail))

    monkeypatch.setattr("keprix.security.event_reporter.report_security_event", capture)

    ok = await apply_proposal("llm-swap-test", "tester")
    assert ok
    env_content = overrides_env_file().read_text()
    assert "KEPRIX_DEFAULT_LLM_PROVIDER=groq" in env_content
    assert any(event[0] == "config_proposal_applied" for event in events)


@pytest.mark.asyncio
async def test_natural_language_health_query(monkeypatch):
    monitor = ConfigHealthMonitor()
    monkeypatch.setattr(
        monitor,
        "_run_all_checks",
        AsyncMock(
            side_effect=lambda: monitor._results.update(
                {
                    "redis": ComponentHealth(
                        name="redis",
                        status="down",
                        latency_ms=0,
                        error="connection refused",
                        checked_at=1.0,
                    )
                }
            )
        ),
    )
    monkeypatch.setattr(
        "keprix.agents.self_config_agent.ConfigHealthMonitor",
        lambda: monitor,
    )
    response = await handle_self_config_request(
        "check your health",
        session_id="sess-1",
        authorized_by="admin",
    )
    assert "redis" in response
    assert "connection refused" in response


def test_is_self_config_request_detects_keywords():
    assert is_self_config_request("Can you check your health?")
    assert not is_self_config_request("What is the weather today?")

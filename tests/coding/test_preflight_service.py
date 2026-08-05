"""Prompt 271 coding preflight service tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.coding.preflight_config import PreflightConfig
from keprix.coding.preflight_service import PreflightService
from keprix.coding.preflight_store import PreflightStore
from keprix.public_api.auth import require_developer_session


def test_preflight_runs_all_gates_and_persists_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    repo = tmp_path / "repo"
    repo.mkdir()
    config = PreflightConfig(diff_budget_lines=100, provider_budget_warn_pct=80)

    report = PreflightService(config=config).run(
        session_id="s1",
        payload={
            "intent": "Add search",
            "repo_path": str(repo),
            "repo_index_present": False,
            "recent_user_messages": ["Add search"],
            "changed_files": ["src/search.py"],
            "planned_lines": 120,
            "provider_budget_pct": 90,
        },
    )

    assert {result.gate for result in report.results} == {
        "repo_index",
        "duplicate_task",
        "test_exists",
        "diff_budget",
        "provider_budget",
    }
    assert report.overall == "block"
    assert report.tokens_saved_estimate >= 1000
    assert PreflightStore().get("s1") is not None


def test_preflight_override_clears_block(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    service = PreflightService(config=PreflightConfig(diff_budget_lines=10))
    service.run(session_id="s1", payload={"planned_lines": 20})

    overridden = service.override("s1")

    assert overridden is not None
    assert overridden.overall == "warn"
    assert overridden.override_applied is True


def test_provider_budget_warns(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    report = PreflightService(config=PreflightConfig(provider_budget_warn_pct=85)).run(
        session_id="s1",
        payload={"provider_budget_pct": 90, "repo_index_present": True, "tests_present": True},
    )

    provider = next(result for result in report.results if result.gate == "provider_budget")
    assert provider.status == "warn"


def test_preflight_api_run_get_and_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_CODING_PREFLIGHT", "1")
    app = create_app()
    app.dependency_overrides[require_developer_session] = lambda: "developer"
    client = TestClient(app)

    response = client.post("/api/coding/preflight/run", json={"session_id": "s1", "planned_lines": 999})
    assert response.status_code == 200
    assert response.json()["report"]["overall"] == "block"

    fetched = client.get("/api/coding/preflight/s1")
    assert fetched.status_code == 200
    assert fetched.json()["report"]["session_id"] == "s1"

    override = client.post("/api/coding/preflight/s1/override")
    assert override.status_code == 200
    assert override.json()["report"]["overall"] == "warn"


def test_preflight_records_ledger_entry(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    report = PreflightService(config=PreflightConfig(diff_budget_lines=10)).run(
        session_id="s1",
        payload={"planned_lines": 50},
    )

    ledger = tmp_path / ".keprix" / "agent-os" / "run-ledger" / "entries"
    manifests = list(ledger.glob("*.json"))
    assert report.tokens_saved_estimate > 0
    assert manifests

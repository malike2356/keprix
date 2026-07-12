"""Prompt 262 headless run service tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.agent_os.headless_run_service import HeadlessRunService
from keprix.agent_os.run_ledger_store import RunLedgerStore
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


@pytest.fixture
def action_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".keprix"
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    skill = home / "skills" / "daily-brief"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Daily brief\n\nSummarize the morning.\n", encoding="utf-8")
    playbook_root = home / "playbooks" / "promoted"
    playbook_root.mkdir(parents=True)
    (playbook_root / "brief.yaml").write_text(
        "id: brief\nentry: done\nsteps:\n- id: done\n  type: task\n  config:\n    set:\n      _eval_score: 0.9\n      _token_usage:\n        total_tokens: 33\n",
        encoding="utf-8",
    )
    app_dir = home / "agent-apps" / "standup" / "agents"
    app_dir.mkdir(parents=True)
    (home / "agent-apps" / "standup" / "agent.yaml").write_text(
        "name: standup\nversion: 1.0.0\nruntime: python\nentrypoint: agents.main:run\n",
        encoding="utf-8",
    )
    (home / "agent-apps" / "standup" / "instructions.md").write_text("Run the standup app.\n", encoding="utf-8")
    (home / "agent-apps" / "standup" / "README.md").write_text("# Standup\n", encoding="utf-8")
    (app_dir / "main.py").write_text(
        "def run(input_text, context=None):\n    return {'text': input_text or 'ok', 'status': 'ok'}\n",
        encoding="utf-8",
    )
    return home


@pytest.mark.asyncio
async def test_headless_skill_run_writes_ledger(action_home: Path) -> None:
    result = await HeadlessRunService().run_skill("daily-brief", {"workspace_id": "default"})

    assert result.status == "completed"
    assert result.ledger_entry_id
    entry = RunLedgerStore().get(result.ledger_entry_id)
    assert entry is not None
    assert entry.source_type == "skill"
    assert entry.tokens > 0


@pytest.mark.asyncio
async def test_headless_playbook_run_uses_runtime_and_ledger(action_home: Path) -> None:
    result = await HeadlessRunService().run_playbook("brief", {"workspace_id": "default"})

    assert result.status == "completed"
    assert result.output["graph_id"] == "brief"
    assert result.ledger_entry_id
    assert RunLedgerStore().get(result.ledger_entry_id).tokens == 33


@pytest.mark.asyncio
async def test_headless_agent_app_run_writes_ledger(action_home: Path) -> None:
    result = await HeadlessRunService().run_agent_app("standup", {"input": "hello"})

    assert result.status == "completed"
    assert result.output["app"] == "standup"
    assert result.ledger_entry_id
    assert RunLedgerStore().get(result.ledger_entry_id).source_type == "agent_app"


def test_action_board_and_run_routes(action_home: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    pin = client.post("/api/agent-os/board/pins", json={"type": "skill", "id": "daily-brief", "label": "Morning brief", "shortcut": "Ctrl+Shift+B"})
    assert pin.status_code == 200
    board = client.get("/api/agent-os/board")
    assert board.status_code == 200
    assert board.json()["config"]["pins"][0]["id"] == "daily-brief"
    run = client.post("/api/agent-os/run/skill/daily-brief", json={"params": {"workspace_id": "default"}})
    assert run.status_code == 200
    status = client.get(f"/api/agent-os/run/{run.json()['run_id']}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"


def test_schedule_route_uses_promoter(action_home: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    response = client.post(
        "/api/agent-os/board/schedule",
        json={"skill_slug": "daily-brief", "schedule": "every 1h", "name": "Morning brief"},
    )

    assert response.status_code == 200
    assert response.json()["automation_type"] == "cron"

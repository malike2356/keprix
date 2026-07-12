"""Prompt 262 Action Board store tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.agent_os.action_board_store import ActionBoardStore
from keprix.agent_os.hooks import record_external_run
from keprix.agent_os.shortcut_registry import normalize_shortcut


def test_action_board_pin_roundtrip_and_shortcut_normalization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    store = ActionBoardStore()

    config = store.add_pin("u1", action_type="skill", action_id="daily-brief", label="Morning brief", shortcut="control+shift+b")

    loaded = store.load("u1")
    assert loaded.pins[0].label == "Morning brief"
    assert loaded.pins[0].shortcut == "Ctrl+Shift+B"
    assert config.shortcuts == {"daily-brief": "Ctrl+Shift+B"}


def test_action_board_rejects_duplicate_shortcuts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    store = ActionBoardStore()
    store.add_pin("u1", action_type="skill", action_id="a", shortcut="Ctrl+Shift+A")

    with pytest.raises(ValueError, match="Duplicate shortcut"):
        store.add_pin("u1", action_type="skill", action_id="b", shortcut="control+shift+a")


def test_action_board_actions_and_metrics_from_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / ".keprix"
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    skill_dir = home / "skills" / "daily-brief"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Daily brief\n", encoding="utf-8")
    playbook_dir = home / "playbooks" / "promoted"
    playbook_dir.mkdir(parents=True)
    (playbook_dir / "daily.yaml").write_text("id: daily\nsteps:\n- id: done\n  type: task\n  config:\n    set:\n      ok: true\n", encoding="utf-8")
    app_dir = home / "agent-apps" / "standup"
    app_dir.mkdir(parents=True)
    (app_dir / "agent.yaml").write_text("name: standup\nversion: 1.0.0\nruntime: python\nentrypoint: agents.main:run\n", encoding="utf-8")
    record_external_run(source_type="skill", source_id="daily-brief", run_id="r1", workspace_id="default", status="completed", tokens=42)
    record_external_run(source_type="skill", source_id="daily-brief", run_id="r2", workspace_id="default", status="failed")

    store = ActionBoardStore()
    actions = store.all_actions()
    metrics = store.metrics()

    assert {"type": "skill", "id": "daily-brief", "label": "daily-brief", "edit_url": "/skills/daily-brief"} in actions
    assert metrics["token_burn_24h"] == 42
    assert metrics["runs_today"] == 2
    assert metrics["failed_runs"] == 1


def test_normalize_shortcut_empty() -> None:
    assert normalize_shortcut("") is None

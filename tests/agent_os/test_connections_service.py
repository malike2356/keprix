"""Prompt 277 connections service tests."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.agent_os.connections_service import ConnectionsService
from keprix.agent_os.maturity_scorers import score_connections


def test_init_template_creates_md_and_json(tmp_path: Path) -> None:
    result = ConnectionsService().init_template(workspace_path=str(tmp_path), seed_tools=["google-workspace"])

    assert (tmp_path / "connections.md").is_file()
    assert (tmp_path / "connections.json").is_file()
    assert len(result["domains"]) == 7
    assert json.loads((tmp_path / "connections.json").read_text(encoding="utf-8"))["domains"][0]["id"] == "revenue"


def test_update_live_domain_feeds_maturity_scorer(tmp_path: Path) -> None:
    service = ConnectionsService()
    service.init_template(workspace_path=str(tmp_path))
    service.update_domain("calendar", status="live", tools=["google-workspace"], workspace_path=str(tmp_path))
    service.update_domain("comms", status="live", tools=["google-workspace"], workspace_path=str(tmp_path))

    score, missing = score_connections(tmp_path)

    assert score.score == 7.0
    assert "calendar" not in missing


def test_suggest_priority_returns_three_with_rationale(tmp_path: Path) -> None:
    service = ConnectionsService()
    service.init_template(workspace_path=str(tmp_path))

    suggestions = service.suggest_priority(workspace_path=str(tmp_path))

    assert len(suggestions) == 3
    assert all(item["rationale"] for item in suggestions)

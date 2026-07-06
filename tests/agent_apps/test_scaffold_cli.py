"""CLI scaffold tests for agent apps."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.agent_apps.registry import AgentAppRegistry
from keprix.agent_apps.scaffold import create_agent_app, slugify_name
from keprix.keprix_cli import agent_app_commands


def test_slugify_name():
    assert slugify_name("My Cool App") == "my-cool-app"


def test_create_agent_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    dest = tmp_path / "demo-app"
    result = create_agent_app(dest, "demo-app", template="agent")
    assert result["valid"] is True
    assert (dest / "agent.yaml").is_file()
    assert (dest / "instructions.md").is_file()
    assert (dest / "tools" / "sample.yaml").is_file()


def test_create_python_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    dest = tmp_path / "py-app"
    result = create_agent_app(dest, "py-app", template="python")
    assert result["valid"] is True
    assert (dest / "agents" / "main.py").is_file()


def test_cli_catalog_list(capsys) -> None:
    code = agent_app_commands.cmd_agent_app_catalog_list(type("Args", (), {})())
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    ids = {item["id"] for item in payload["templates"]}
    assert "daily-standup" in ids


def test_cli_create_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    dest = tmp_path / "cli-app"
    args = type("Args", (), {"name": "cli-app", "path": str(dest), "template": "agent", "force": False})()
    code = agent_app_commands.cmd_agent_app_create(args)
    assert code == 0
    assert (dest / "agent.yaml").is_file()

"""Tests for keprix upgrade CLI handlers."""

from __future__ import annotations

import argparse
from pathlib import Path

from keprix.keprix_cli.upgrade_commands import _resolve_upgrade_action, cmd_upgrade


def _write_product(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "keprix.yaml").write_text(
        """
product:
  name: CliProduct
  slug: cliproduct
keprix:
  min_version: "0.2.0"
  tested_against: "0.3.0"
features: {}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_resolve_upgrade_action_execute():
    args = argparse.Namespace(
        check=False, plan=False, list=False, dry_run=False,
        rollback=False, prompt_name=None, to="0.7.0",
    )
    assert _resolve_upgrade_action(args) == "execute"


def test_resolve_upgrade_action_check_with_target():
    args = argparse.Namespace(
        check=True, plan=False, list=False, dry_run=False,
        rollback=False, prompt_name=None, to="0.7.0",
    )
    assert _resolve_upgrade_action(args) == "check"


def test_resolve_upgrade_action_rejects_multiple():
    args = argparse.Namespace(
        check=True, plan=True, list=False, dry_run=False,
        rollback=False, prompt_name=None, to=None,
    )
    try:
        _resolve_upgrade_action(args)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_cmd_upgrade_check_json(tmp_path: Path, monkeypatch, capsys):
    _write_product(tmp_path)
    monkeypatch.setattr("keprix.upgrade.context.installed_keprix_version", lambda: "0.3.0")
    args = argparse.Namespace(
        path=str(tmp_path),
        check=True,
        plan=False,
        list=False,
        dry_run=False,
        rollback=False,
        prompt_name=None,
        to="0.7.0",
        json=True,
        force=False,
        yes=False,
        skip_tests=False,
        step=False,
    )
    code = cmd_upgrade(args)
    out = capsys.readouterr().out
    assert code == 0
    assert '"risk"' in out
    assert "CliProduct" in out


def test_cmd_upgrade_plan_human(tmp_path: Path, monkeypatch, capsys):
    _write_product(tmp_path)
    monkeypatch.setattr("keprix.upgrade.context.installed_keprix_version", lambda: "0.3.0")
    args = argparse.Namespace(
        path=str(tmp_path),
        check=False,
        plan=True,
        list=False,
        dry_run=False,
        rollback=False,
        prompt_name=None,
        to="0.7.0",
        json=False,
        force=False,
        yes=False,
        skip_tests=False,
        step=False,
    )
    code = cmd_upgrade(args)
    out = capsys.readouterr().out
    assert code == 0
    assert "Upgrade Path" in out
    assert "0.4.0" in out


def test_cmd_upgrade_list_prompts(capsys):
    args = argparse.Namespace(
        path=None,
        check=False,
        plan=False,
        list=False,
        list_prompts=True,
        dry_run=False,
        rollback=False,
        prompt_name=None,
        to=None,
        json=False,
        force=False,
        yes=False,
        skip_tests=False,
        step=False,
    )
    code = cmd_upgrade(args)
    out = capsys.readouterr().out
    assert code == 0
    assert "adopt-billing" in out
    assert "adopt-routing" in out


def test_cmd_upgrade_prompt_apply(tmp_path: Path, monkeypatch):
    _write_product(tmp_path)
    monkeypatch.setattr("keprix.upgrade.context.installed_keprix_version", lambda: "0.3.0")
    args = argparse.Namespace(
        path=str(tmp_path),
        check=False,
        plan=False,
        list=False,
        dry_run=False,
        rollback=False,
        prompt_name="adopt-routing",
        to=None,
        json=True,
        force=False,
        yes=True,
        skip_tests=False,
        step=False,
    )
    assert cmd_upgrade(args) == 0
    manifest = (tmp_path / "keprix.yaml").read_text(encoding="utf-8")
    assert "routing" in manifest

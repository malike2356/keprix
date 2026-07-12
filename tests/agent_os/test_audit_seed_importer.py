"""Prompt 264 audit seed importer tests."""

from __future__ import annotations

import argparse
from pathlib import Path

from keprix.agent_os.audit_seed_importer import import_audit_seed
from keprix.agent_os.cli_commands import _dispatch_audit


SEED = Path("packages/packs/keprix-personal-os-starter/audit-seed.json")


def test_audit_seed_importer_creates_editable_draft(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    audit = import_audit_seed(SEED, user_id="u1")

    assert audit.status == "draft"
    assert audit.mode == "manual"
    assert len(audit.tasks) >= 3
    assert audit.tasks[0].propose_automation is True


def test_agent_os_audit_import_cli(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    args = argparse.Namespace(audit_command="import", seed=str(SEED))

    assert _dispatch_audit(args) == 0
    output = capsys.readouterr().out
    assert "daily-brief" in output

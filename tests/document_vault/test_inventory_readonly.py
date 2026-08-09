"""Read-only inventory audit tests (Prompt 645)."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.document_vault.compatibility import list_adapters
from keprix.document_vault.inventory import build_inventory_report


def test_inventory_report_is_read_only_and_complete(tmp_path: Path) -> None:
    report = build_inventory_report("ws_audit", dry_run=True)
    assert report["mutated"] is False
    assert report["dry_run"] is True
    assert report["carina_runtime_required"] is False
    assert report["document_vault_ready"] is False
    assert report["surfaces"]["total"] >= 15
    assert report["surfaces"]["present"] == report["surfaces"]["total"]
    assert report["surfaces"]["missing"] == []
    assert "duplicate_ids" in report["duplicates"]
    assert "versions_without_parent" in report["orphans"]
    assert report["flags"]["KEPRIX_DOCUMENT_VAULT_HOST_FS_BRIDGE"] is False


def test_inventory_cli_module_main(capsys) -> None:
    from keprix.document_vault.inventory import main

    code = main(["--workspace-id", "cli-ws"])
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["mutated"] is False
    assert payload["workspace_id"] == "cli-ws"


def test_adapters_exclude_host_fs_target() -> None:
    adapters = list_adapters()
    fs = next(a for a in adapters if a["caller"] == "/api/fs")
    assert fs["target"] == "NONE"
    assert fs["status"] == "retired"

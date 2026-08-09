"""Document Vault programme close and conformance tests (Prompt 653)."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.document_vault.conformance import build_conformance_matrix, run_ce_offline_smoke
from keprix.document_vault.ready import document_vault_ready


def test_programme_ready() -> None:
    assert document_vault_ready() is True


def test_ce_offline_smoke_green() -> None:
    result = run_ce_offline_smoke()
    assert result["ok"] is True
    assert result["cross_tenant_leak"] is False
    assert result["backup_verified"] is True
    assert result["restored"] is True


def test_conformance_matrix_green(tmp_path: Path, monkeypatch) -> None:
    # Write evidence under tmp by monkeypatching ROOT is heavy; use write_evidence True
    # into repo evidence dir (product evidence file is intentional for 653).
    report = build_conformance_matrix(write_evidence=True)
    assert report["document_vault_ready"] is True
    assert report["summary"]["green"] is True
    assert report["summary"]["failed"] == 0
    evidence = Path(report["evidence_path"])
    assert evidence.is_file()
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["summary"]["green"] is True
    # Honesty: no false-live Google claim
    honesty = " ".join(payload.get("honesty") or [])
    assert "BLOCKED_OPTIONAL_CREDENTIALS" in honesty or "credentials" in honesty.lower()

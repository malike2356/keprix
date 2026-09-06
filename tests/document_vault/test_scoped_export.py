from __future__ import annotations

import io
import zipfile

from keprix.document_vault.channel.scoped_export import build_scoped_zip, destination_status
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.store import DocumentVaultStore


def test_scoped_export_filters_by_kind(tmp_path):
    store = DocumentVaultStore(tmp_path / "vault.sqlite")
    service = DocumentVaultService(store=store)
    service.create_text_item("ws1", "note.md", "note", kind="markdown")
    service.create_text_item("ws1", "brief.txt", "brief", kind="plain_text")
    service.create_text_item("ws1", "report.pdf", "report", kind="pdf")
    filename, data, count = build_scoped_zip("ws1", "notes", store=store, service=service)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert "manifest.json" in archive.namelist()
        names = [n for n in archive.namelist() if n != "manifest.json"]
        assert len(names) == 2
        assert all(name.startswith(("markdown/", "plain_text/")) for name in names)
    assert filename == "keprix-ws1-notes.zip"
    assert count == 2


def test_optional_destinations_report_disabled(monkeypatch):
    monkeypatch.delenv("KEPRIX_ONEDRIVE_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("KEPRIX_DROPBOX_ACCESS_TOKEN", raising=False)
    status = destination_status()
    assert status["local"]["enabled"] is True
    assert status["onedrive"]["enabled"] is False
    assert status["dropbox"]["enabled"] is False

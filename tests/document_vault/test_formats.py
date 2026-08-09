"""Format engine tests (Prompt 647)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.document_vault.formats.engines import export_text, import_bytes_to_text, render_pdf_bytes
from keprix.document_vault.formats.registry import capability_matrix_for_clients, resolve_format
from keprix.document_vault.formats.safety import validate_upload
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.storage import LocalStorageAdapter
from keprix.document_vault.store import reset_document_vault_store_for_tests


@pytest.fixture()
def vault(tmp_path: Path) -> DocumentVaultService:
    store = reset_document_vault_store_for_tests(tmp_path / "v.sqlite")
    return DocumentVaultService(store=store, storage=LocalStorageAdapter(root=tmp_path / "blobs"))


def test_capability_matrix_lists_ce_core() -> None:
    matrix = capability_matrix_for_clients()
    ids = {f["format_id"] for f in matrix["formats"]}
    assert {"markdown", "html", "plain_text", "pdf", "csv"}.issubset(ids)
    assert "markdown" in matrix["ce_core"]
    pptx = resolve_format(format_id="pptx")
    assert pptx and pptx.fidelity == "blocked_optional"


def test_markdown_round_trip_export_html_pdf(vault: DocumentVaultService) -> None:
    item = vault.create_text_item("ws", "note.md", "# Hello\n\nWorld")
    html = export_text("# Hello", source_kind="markdown", target_format="html", title="T")
    assert b"<html" in html["data"].lower() or b"Hello" in html["data"]
    pdf = vault.generate_pdf_artifact("ws", item["id"])
    assert pdf["source_unchanged"] is True
    assert pdf["artifact"]["kind"] == "pdf"
    meta = pdf["artifact"].get("metadata") or {}
    assert meta.get("source_item_id") == item["id"]
    assert meta.get("source_revision") == item["current_revision"]
    # Source body unchanged
    assert vault.read_text("ws", item["id"]) == "# Hello\n\nWorld"


def test_import_keeps_original_and_derived(vault: DocumentVaultService) -> None:
    data = b"# Imported\n"
    result = vault.import_bytes("ws", data, filename="doc.md", declared_mime="text/markdown")
    assert result["source_preserved"] is True
    assert result["original"]["kind"] == "binary_upload"
    assert result["derived"]["kind"] == "markdown"
    assert vault.read_text("ws", result["derived"]["id"]).startswith("# Imported")
    # Original bytes intact
    assert vault.read_bytes("ws", result["original"]["id"]) == data


def test_spoofed_mime_rejected() -> None:
    with pytest.raises(VaultError) as ei:
        validate_upload(b"%PDF-1.4\n", filename="note.md", declared_mime="text/markdown")
    assert ei.value.code == "unsupported_kind"


def test_oversized_rejected() -> None:
    with pytest.raises(VaultError) as ei:
        validate_upload(b"x" * 100, filename="a.txt", declared_mime="text/plain", max_bytes=10)
    assert ei.value.code == "quota_exceeded"


def test_macro_docx_rejected() -> None:
    # Minimal zip claiming docx with vbaProject.bin
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<xml/>")
        zf.writestr("word/vbaProject.bin", b"MZ")
    with pytest.raises(VaultError) as ei:
        validate_upload(buf.getvalue(), filename="macro.docx")
    assert ei.value.code == "unsupported_kind"


def test_pptx_import_not_configured() -> None:
    with pytest.raises(VaultError) as ei:
        import_bytes_to_text(b"PK\x03\x04fake", filename="deck.pptx")
    assert ei.value.code in {"not_configured", "unsupported_kind"}


def test_corrupt_input_fails_safely() -> None:
    with pytest.raises(VaultError):
        import_bytes_to_text(b"not-a-docx", filename="bad.docx", declared_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def test_pdf_render_deterministic_enough() -> None:
    a = render_pdf_bytes("# Same", title="T", source_kind="markdown")
    b = render_pdf_bytes("# Same", title="T", source_kind="markdown")
    assert a["data"][:4] == b"%PDF"
    assert len(a["data"]) == len(b["data"])

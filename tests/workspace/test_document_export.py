"""Tests for workspace document export helpers."""

from __future__ import annotations

from keprix.workspace.document_helpers import export_document
from keprix.workspace.pdf_export import render_text_pdf


def test_render_text_pdf_produces_valid_header():
    payload = render_text_pdf("Title", "Hello world")
    assert payload.startswith(b"%PDF-1.4")
    assert payload.endswith(b"%%EOF\n")


def test_export_document_pdf_returns_bytes():
    media_type, payload = export_document({"title": "Notes", "content": "Line one\nLine two"}, "pdf")
    assert media_type == "application/pdf"
    assert isinstance(payload, bytes)
    assert payload.startswith(b"%PDF")

"""Tests for export renderer: cover page, signatory, document_id, structured_json."""

from __future__ import annotations

import json

from keprix.export.cover_page import generate_cover_html, generate_signatory_html
from keprix.export.pdf_engine import render_pdf
from keprix.export.renderer import (
    _strip_remote_images,
    export_document,
    markdown_to_html,
    structured_json_to_html,
)


# ---- Sanitization ----

def test_markdown_to_html_sanitizes_script() -> None:
    doc = markdown_to_html("# Title\n\n<script>alert(1)</script>", title="Title")
    assert "<script>" not in doc
    assert "Title" in doc


def test_strip_remote_images_removes_http_image() -> None:
    source = "Text ![pic](https://example.com/img.png) more"
    result = _strip_remote_images(source)
    assert "https://example.com/img.png" not in result
    assert "Text" in result


def test_strip_remote_images_leaves_local_paths() -> None:
    source = "Text ![pic](./local/img.png) more"
    result = _strip_remote_images(source)
    assert "./local/img.png" in result


# ---- Cover page ----

def test_cover_html_contains_title() -> None:
    cover = generate_cover_html(title="My Report", document_type="Hazard Log")
    assert "My Report" in cover
    assert "Hazard Log" in cover


def test_cover_html_contains_generated_date() -> None:
    cover = generate_cover_html(title="Report")
    assert "UTC" in cover


def test_cover_html_omits_empty_fields() -> None:
    cover = generate_cover_html(title="Report")
    assert "Document ID" not in cover
    assert "Classification" not in cover


def test_export_document_includes_cover_in_html() -> None:
    result = export_document(
        title="Covered Doc",
        content="## Section\n\nContent here.",
        format="html",
        include_cover=True,
        cover_data={"document_type": "Compliance Report"},
    )
    assert result["format"] == "html"
    assert "cover-page" in result["content"]
    assert "Compliance Report" in result["content"]


def test_export_document_includes_cover_in_pdf() -> None:
    result = export_document(
        title="Covered Doc",
        content="## Section\n\nContent here.",
        format="pdf",
        include_cover=True,
        cover_data={"document_type": "Deep Research Report", "document_id": "rsch-cover01"},
        html_template="research",
    )
    assert result["content"][:4] == b"%PDF"


# ---- Signatory block ----

def test_signatory_html_contains_reviewer_and_decision() -> None:
    sig = generate_signatory_html({
        "reviewer_name": "Alice Smith",
        "reviewer_role": "Compliance Officer",
        "decision": "approved",
        "timestamp": "2026-07-05T14:00:00Z",
    })
    assert "Alice Smith" in sig
    assert "approved" in sig.lower()
    assert "signatory-legal" in sig


def test_export_document_includes_signatory_in_html() -> None:
    result = export_document(
        title="Signed Doc",
        content="Body text.",
        format="html",
        include_signatory=True,
        signatory_data={
            "reviewer_name": "Bob Jones",
            "decision": "approved",
            "timestamp": "2026-07-05",
        },
    )
    assert "signatory-block" in result["content"]
    assert "Bob Jones" in result["content"]


# ---- document_id input ----

def test_export_document_resolves_document_id() -> None:
    def resolver(doc_id: str) -> str:
        return f"# Resolved Document\n\nContent for {doc_id}"

    result = export_document(
        title="Doc",
        input_type="document_id",
        content="doc-abc123",
        format="html",
        document_resolver=resolver,
    )
    assert result["format"] == "html"
    assert "Resolved Document" in result["content"]
    assert "doc-abc123" in result["content"]


def test_export_document_id_without_resolver_raises() -> None:
    import pytest
    with pytest.raises(ValueError, match="document_resolver"):
        export_document(
            title="Doc",
            input_type="document_id",
            content="doc-123",
            format="html",
        )


# ---- structured_json ----

def test_structured_json_to_html_renders_table() -> None:
    data = {"status": "ok", "score": 95, "category": "low-risk"}
    html = structured_json_to_html(data, title="Report")
    assert "status" in html
    assert "low-risk" in html
    assert "kv-table" in html


def test_export_document_structured_json_renders() -> None:
    payload = json.dumps({"finding": "none", "risk": "low"})
    result = export_document(
        title="Risk Report",
        input_type="structured_json",
        content=payload,
        format="html",
    )
    assert result["format"] == "html"
    assert "finding" in result["content"]
    assert "none" in result["content"]


# ---- PDF engine ----

def test_export_pdf_returns_bytes() -> None:
    result = export_document(
        title="Report",
        content="# Hello\n\nWorld",
        format="pdf",
    )
    assert result["content"][:4] == b"%PDF"


def test_render_pdf_direct() -> None:
    pdf = render_pdf(title="T", markdown_source="Line one")
    assert pdf.startswith(b"%PDF")

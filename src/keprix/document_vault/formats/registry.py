"""Document Vault format capability registry (Prompt 647)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FormatCapability:
    format_id: str
    kind: str | None
    extensions: tuple[str, ...]
    mime_types: tuple[str, ...]
    create: bool
    importable: bool
    exportable: bool
    preview: bool
    pdf: bool
    fidelity: str  # lossless | lossy | partial | blocked_optional
    converter: str
    notes: str = ""


# Core Community Edition formats must not require paid services.
FORMATS: tuple[FormatCapability, ...] = (
    FormatCapability(
        "markdown",
        "markdown",
        (".md", ".markdown"),
        ("text/markdown", "text/x-markdown"),
        True,
        True,
        True,
        True,
        True,
        "lossless",
        "keprix.markdown",
        "CE core",
    ),
    FormatCapability(
        "html",
        "html",
        (".html", ".htm"),
        ("text/html",),
        True,
        True,
        True,
        True,
        True,
        "lossy",
        "keprix.html+nh3",
        "Sanitized HTML preview/export",
    ),
    FormatCapability(
        "plain_text",
        "plain_text",
        (".txt", ".text"),
        ("text/plain",),
        True,
        True,
        True,
        True,
        True,
        "lossless",
        "keprix.text",
    ),
    FormatCapability(
        "rich_document",
        "rich_document",
        (".keprixdoc", ".html"),
        ("application/vnd.keprix.rich-document", "text/html"),
        True,
        True,
        True,
        True,
        True,
        "partial",
        "keprix.rich_html",
        "Stored as sanitized HTML body",
    ),
    FormatCapability(
        "csv",
        "spreadsheet",
        (".csv",),
        ("text/csv", "application/csv"),
        True,
        True,
        True,
        True,
        False,
        "lossless",
        "keprix.csv",
    ),
    FormatCapability(
        "json",
        None,
        (".json",),
        ("application/json",),
        False,
        True,
        True,
        True,
        False,
        "lossless",
        "keprix.json",
        "Import as plain_text or binary_upload",
    ),
    FormatCapability(
        "xlsx",
        "spreadsheet",
        (".xlsx",),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
        True,
        True,
        True,
        False,
        False,
        "partial",
        "openpyxl",
        "Requires keprix[analytics] / openpyxl; else not_configured",
    ),
    FormatCapability(
        "docx",
        "rich_document",
        (".docx",),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
        False,
        True,
        False,
        True,
        True,
        "lossy",
        "python-docx|zipxml",
        "Import to markdown/html; macros rejected",
    ),
    FormatCapability(
        "pdf",
        "pdf",
        (".pdf",),
        ("application/pdf",),
        False,
        True,
        True,
        True,
        True,
        "lossy",
        "weasyprint|pypdf|text_pdf",
        "Generated PDF is revision-linked artifact, never replaces source",
    ),
    FormatCapability(
        "pptx",
        "presentation",
        (".pptx",),
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation",),
        False,
        False,
        False,
        False,
        False,
        "blocked_optional",
        "external",
        "No CE converter; honest not_configured",
    ),
    FormatCapability(
        "odt",
        "rich_document",
        (".odt",),
        ("application/vnd.oasis.opendocument.text",),
        False,
        False,
        False,
        False,
        False,
        "blocked_optional",
        "external",
        "Optional LibreOffice/pandoc when present",
    ),
    FormatCapability(
        "ods",
        "spreadsheet",
        (".ods",),
        ("application/vnd.oasis.opendocument.spreadsheet",),
        False,
        True,
        False,
        False,
        False,
        "partial",
        "odfpy|pandas",
        "Import when analytics extras available",
    ),
    FormatCapability(
        "rtf",
        "rich_document",
        (".rtf",),
        ("application/rtf", "text/rtf"),
        False,
        False,
        False,
        False,
        False,
        "blocked_optional",
        "external",
    ),
    FormatCapability(
        "image",
        "binary_upload",
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"),
        ("image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"),
        False,
        True,
        True,
        True,
        False,
        "lossless",
        "keprix.image",
        "Stored as binary_upload; SVG sanitized on preview",
    ),
)


def list_format_capabilities(*, include_blocked: bool = True) -> list[dict[str, Any]]:
    rows = []
    for fmt in FORMATS:
        if not include_blocked and fmt.fidelity == "blocked_optional":
            continue
        row = asdict(fmt)
        row["extensions"] = list(fmt.extensions)
        row["mime_types"] = list(fmt.mime_types)
        rows.append(row)
    return rows


def capability_matrix_for_clients() -> dict[str, Any]:
    """Compact matrix for web, desktop, TUI, and agents."""
    return {
        "contract_version": "1.0.0",
        "product": "keprix",
        "formats": list_format_capabilities(include_blocked=True),
        "ce_core": [
            f.format_id
            for f in FORMATS
            if f.fidelity in {"lossless", "lossy", "partial"} and (f.create or f.importable)
        ],
        "notes": [
            "PDF artifacts link to source_item_id + source_revision and never overwrite the source.",
            "Blocked optional converters return not_configured without corrupting sources.",
        ],
    }


def resolve_format(*, filename: str = "", mime: str = "", format_id: str = "") -> FormatCapability | None:
    if format_id:
        for fmt in FORMATS:
            if fmt.format_id == format_id:
                return fmt
    name = (filename or "").lower()
    mime_l = (mime or "").lower().split(";")[0].strip()
    for fmt in FORMATS:
        if any(name.endswith(ext) for ext in fmt.extensions):
            return fmt
    for fmt in FORMATS:
        if mime_l and mime_l in fmt.mime_types:
            return fmt
    return None

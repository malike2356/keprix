"""Export document agent tool registration (Prompt 108)."""

from __future__ import annotations

import json
from typing import Any

from keprix.export.renderer import export_document
from keprix.tools.registry import registry

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Convert a document, note, or structured content to PDF or HTML. "
        "Use when you need a formatted, immutable file a human can review or sign. "
        "Returns export metadata including format and size."
    ),
    "properties": {
        "input_type": {
            "type": "string",
            "enum": ["markdown", "document_id", "note_id", "structured_json"],
            "description": "Source format of the content field",
        },
        "content": {
            "type": "string",
            "description": "Markdown text, document/note ID, or JSON string depending on input_type",
        },
        "title": {"type": "string", "description": "Document title"},
        "document_type": {"type": "string", "description": "e.g. Hazard Log, Compliance Report"},
        "version": {"type": "string"},
        "prepared_by": {"type": "string"},
        "include_cover": {"type": "boolean", "default": True},
        "include_signatory": {"type": "boolean", "default": False},
        "signatory_data": {
            "type": "object",
            "description": "Required when include_signatory is true",
        },
        "format": {
            "type": "string",
            "enum": ["pdf", "html"],
            "default": "pdf",
        },
        "classification": {"type": "string", "description": "e.g. CONFIDENTIAL, DRAFT"},
    },
    "required": ["input_type", "content", "title"],
}


def _handle_export(args: dict[str, Any]) -> str:
    input_type = args.get("input_type", "markdown")
    content = args.get("content", "")
    title = args.get("title", "Export")
    fmt = args.get("format", "pdf")

    cover_data: dict[str, Any] = {
        "document_type": args.get("document_type", ""),
        "version": args.get("version", ""),
        "prepared_by": args.get("prepared_by", ""),
        "classification": args.get("classification", ""),
    }

    resolver = None
    if input_type in ("document_id", "note_id"):
        from keprix.export.resolver import make_document_resolver

        resolver = make_document_resolver("local")

    try:
        result = export_document(
            title=title,
            input_type=input_type,
            content=content,
            format=fmt,
            include_cover=bool(args.get("include_cover", True)),
            cover_data=cover_data,
            include_signatory=bool(args.get("include_signatory", False)),
            signatory_data=args.get("signatory_data"),
            document_resolver=resolver,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})

    from keprix.export.store import get_export_store

    fmt_returned = result.get("format_returned", result["format"])
    record = get_export_store().save(
        title=title,
        content=result["content"],
        mime=result["mime"],
        format_returned=fmt_returned,
    )
    output: dict[str, Any] = {
        "format_returned": fmt_returned,
        "title": title,
        "file_id": record.file_id,
        "file_url": f"/api/export/{record.file_id}",
        "size_bytes": record.size_bytes,
    }
    return json.dumps(output)


registry.register(
    name="export_document",
    toolset="export",
    schema=_SCHEMA,
    handler=_handle_export,
    description=(
        "Convert a document, note, or structured content to PDF or HTML. "
        "Returns a formatted, immutable export suitable for review or sign-off."
    ),
)

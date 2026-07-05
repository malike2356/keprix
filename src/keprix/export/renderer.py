"""Markdown and HTML export rendering."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Callable
from typing import Any

import markdown
import nh3


def markdown_to_html(source: str, *, title: str = "") -> str:
    """Convert Markdown to sanitized HTML."""
    source = _strip_remote_images(source)
    body = markdown.markdown(
        source,
        extensions=["fenced_code", "tables", "toc", "nl2br"],
        output_format="html5",
    )
    safe_body = nh3.clean(
        body,
        tags=nh3.ALLOWED_TAGS
        | {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "pre",
            "code",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "blockquote",
            "hr",
            "img",
        },
        attributes={"*": {"class", "id"}, "a": {"href", "title"}, "img": {"src", "alt", "title"}},
        link_rel=None,
    )
    page_title = html.escape(title or "Export")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{page_title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; line-height: 1.55; }}
    pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem; }}
  </style>
</head>
<body>
{safe_body}
</body>
</html>"""


def _strip_remote_images(source: str) -> str:
    """Remove Markdown image links with http/https URLs."""
    return re.sub(r"!\[[^\]]*\]\(https?://[^)]+\)", "", source)


def structured_json_to_html(data: dict[str, Any] | str, *, title: str = "") -> str:
    """Render a structured JSON object as a two-column key-value HTML table."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, ValueError):
            data = {"raw": data}

    def _render_value(value: Any) -> str:
        if isinstance(value, dict):
            inner = "".join(
                f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
                for k, v in value.items()
            )
            return f'<table class="nested">{inner}</table>'
        if isinstance(value, list):
            items = "".join(f"<li>{html.escape(str(item))}</li>" for item in value)
            return f"<ul>{items}</ul>"
        return html.escape(str(value))

    rows = "".join(
        f"<tr><td class='kv-key'>{html.escape(str(k))}</td>"
        f"<td class='kv-val'>{_render_value(v)}</td></tr>"
        for k, v in (data.items() if isinstance(data, dict) else {})
    )
    page_title = html.escape(title or "Structured Report")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{page_title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; line-height: 1.55; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem; }}
    .kv-key {{ font-weight: bold; width: 35%; vertical-align: top; }}
    .nested {{ width: 100%; margin: 0; }}
    ul {{ margin: 0; padding-left: 1.2rem; }}
  </style>
</head>
<body>
<h1>{page_title}</h1>
<table class="kv-table"><tbody>{rows}</tbody></table>
</body>
</html>"""


def strip_markdown(source: str) -> str:
    """Best-effort plain text extraction for PDF fallback."""
    text = re.sub(r"```.*?```", "", source, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def export_document(
    *,
    title: str,
    input_type: str = "markdown",
    content: str = "",
    markdown_source: str = "",
    format: str = "html",
    include_cover: bool = False,
    cover_data: dict[str, Any] | None = None,
    include_signatory: bool = False,
    signatory_data: dict[str, Any] | None = None,
    document_resolver: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Render export in the requested format.

    Parameters
    ----------
    input_type:
        One of 'markdown', 'document_id', 'note_id', 'structured_json'.
    content:
        The raw content string. For document_id/note_id, this is the ID.
    markdown_source:
        Legacy positional Markdown string (used when input_type is not supplied).
    document_resolver:
        Optional callable(id) -> markdown_text for resolving document_id/note_id.
    """
    source = markdown_source or content

    if input_type in ("document_id", "note_id"):
        if document_resolver is None:
            raise ValueError(f"document_resolver is required for input_type={input_type!r}")
        source = document_resolver(source)
        input_type = "markdown"

    fmt = format.lower().strip()

    if input_type == "structured_json":
        html_doc = structured_json_to_html(source, title=title)
    else:
        html_doc = markdown_to_html(source, title=title)

    if include_cover:
        from keprix.export.cover_page import generate_cover_html
        cover_html = generate_cover_html(
            title=title,
            **(cover_data or {}),
        )
        html_doc = _inject_after_body_open(html_doc, cover_html)

    if include_signatory and signatory_data:
        from keprix.export.cover_page import generate_signatory_html
        sig_html = generate_signatory_html(signatory_data)
        html_doc = _inject_before_body_close(html_doc, sig_html)

    if fmt == "markdown":
        return {"format": "markdown", "content": source, "mime": "text/markdown"}
    if fmt == "html":
        return {"format": "html", "content": html_doc, "mime": "text/html"}
    if fmt == "pdf":
        from keprix.export.pdf_engine import render_pdf
        try:
            pdf_bytes = render_pdf(title=title, markdown_source=source)
            return {"format": "pdf", "content": pdf_bytes, "mime": "application/pdf"}
        except Exception:
            return {"format": "html", "content": html_doc, "mime": "text/html", "format_returned": "html"}
    raise ValueError(f"Unsupported export format: {format}")


def _inject_after_body_open(html_doc: str, fragment: str) -> str:
    return html_doc.replace("<body>", f"<body>\n{fragment}", 1)


def _inject_before_body_close(html_doc: str, fragment: str) -> str:
    return html_doc.replace("</body>", f"{fragment}\n</body>", 1)

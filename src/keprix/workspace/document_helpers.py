"""Document helper utilities."""

from __future__ import annotations

import html
import secrets
from typing import Any

from keprix.workspace.pdf_export import render_text_pdf


def word_count(content: str) -> int:
    text = content.strip()
    if not text:
        return 0
    return len(text.split())


def document_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        **doc,
        "word_count": word_count(doc.get("content", "")),
    }


def apply_ai_edit(content: str, instruction: str) -> str:
    instruction = instruction.strip()
    if not instruction:
        return content
    if content.startswith("#"):
        return f"{content}\n\n<!-- AI edit: {instruction} -->\n"
    return f"<!-- AI edit: {instruction} -->\n\n{content}"


def ai_suggest(content: str) -> list[str]:
    suggestions = []
    if len(content) < 40:
        suggestions.append("Expand this section with more detail.")
    if "#" not in content and len(content.split()) > 80:
        suggestions.append("Consider adding headings to improve structure.")
    if not suggestions:
        suggestions.append("Content looks good. Consider adding a summary paragraph.")
    return suggestions


def export_document(doc: dict[str, Any], fmt: str) -> tuple[str, str | bytes]:
    content = doc.get("content", "")
    title = doc.get("title", "document")
    if fmt == "html":
        body = html.escape(content).replace("\n", "<br>\n")
        return f"text/html; charset=utf-8", f"<html><body><h1>{html.escape(title)}</h1><div>{body}</div></body></html>"
    if fmt == "txt":
        return "text/plain; charset=utf-8", content
    if fmt == "pdf":
        return "application/pdf", render_text_pdf(title, content)
    return "text/markdown; charset=utf-8", content


def generate_share_token() -> str:
    return secrets.token_urlsafe(24)

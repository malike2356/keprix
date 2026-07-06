"""PDF export engine with HTML-first fallback."""

from __future__ import annotations

from keprix.export.renderer import markdown_to_html, strip_markdown
from keprix.workspace.pdf_export import render_text_pdf


def weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401

        return True
    except Exception:
        return False


def render_pdf_from_html(html_doc: str, *, fallback_title: str = "Export", fallback_markdown: str = "") -> bytes:
    """Render PDF bytes from composed HTML (cover page, signatory, custom CSS)."""
    if weasyprint_available():
        import weasyprint  # type: ignore[import-untyped]

        return weasyprint.HTML(string=html_doc).write_pdf()
    plain = strip_markdown(fallback_markdown) if fallback_markdown else fallback_title
    return render_text_pdf(fallback_title, plain)


def render_pdf(*, title: str, markdown_source: str) -> bytes:
    """Render PDF bytes from Markdown source."""
    html_doc = markdown_to_html(markdown_source, title=title)
    return render_pdf_from_html(html_doc, fallback_title=title, fallback_markdown=markdown_source)

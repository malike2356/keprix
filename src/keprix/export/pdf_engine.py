"""PDF export engine with HTML-first fallback."""

from __future__ import annotations

from keprix.export.renderer import markdown_to_html, strip_markdown
from keprix.workspace.pdf_export import render_text_pdf


def render_pdf(*, title: str, markdown_source: str) -> bytes:
    """Render PDF bytes from Markdown source."""
    try:
        import weasyprint  # type: ignore[import-untyped]

        html_doc = markdown_to_html(markdown_source, title=title)
        return weasyprint.HTML(string=html_doc).write_pdf()
    except Exception:
        plain = strip_markdown(markdown_source)
        return render_text_pdf(title, plain)

"""Export deep research jobs to PDF, HTML, Markdown, and DOCX."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.export.renderer import export_document, markdown_to_html
from keprix.research.store import ResearchJob

ResearchExportFormat = Literal["pdf", "html", "markdown", "docx"]

_INTERNAL_HEADER_RE = re.compile(r"^<!--\s*keprix-research.*?-->\s*", re.IGNORECASE | re.DOTALL)
_SYNTHESIS_HEADER_RE = re.compile(
    r"^#\s*Research Report\s*\n+(?:\*\*Query:\*\*[^\n]*\n+)?"
    r"(?:\*\*Depth:\*\*[^\n]*\n+)?(?:\*\*Generated in:\*\*[^\n]*\n+)?\s*",
    re.IGNORECASE | re.MULTILINE,
)


def _strip_internal_header(markdown: str) -> str:
    return _INTERNAL_HEADER_RE.sub("", markdown).lstrip()


def _normalize_report_body(markdown: str) -> str:
    """Remove duplicate Keprix synthesis headers; keep the substantive report."""
    body = _strip_internal_header(markdown)
    body = _SYNTHESIS_HEADER_RE.sub("", body, count=1).lstrip()
    return body


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build_research_export_markdown(job: ResearchJob, *, include_front_matter: bool = False) -> str:
    """Prepare stored report Markdown for export."""
    body = _normalize_report_body(job.report_markdown or "")
    if not include_front_matter:
        return body

    generated = _format_timestamp(job.completed_at or job.started_at)
    source_count = len(job.sources or [])
    front_matter = (
        f"---\n"
        f"title: {research_export_title(job)}\n"
        f"query: {job.query}\n"
        f"depth: {job.depth}\n"
        f"generated: {generated}\n"
        f"sources_reviewed: {source_count}\n"
        f"run_id: {job.id}\n"
        f"---\n\n"
    )
    return front_matter + body


def research_export_title(job: ResearchJob) -> str:
    body = _normalize_report_body(job.report_markdown or "")
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and "research report" not in stripped.lower():
            return stripped.lstrip("# ").strip()[:120]
    return job.query[:80].strip() or "Research Report"


def research_export_filename(job: ResearchJob, fmt: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", job.query.lower()).strip("-")[:40] or "report"
    extension = fmt if fmt != "markdown" else "md"
    return f"research-{slug}-{job.id}.{extension}"


def export_research_job(
    job: ResearchJob,
    *,
    format: ResearchExportFormat = "pdf",
    include_cover: bool = True,
    prepared_by: str | None = None,
    classification: str = "",
) -> dict[str, Any]:
    """Render a research job deliverable in the requested format."""
    if not job.report_markdown:
        raise ValueError("Report not ready")

    markdown = build_research_export_markdown(
        job,
        include_front_matter=(format == "markdown"),
    )
    title = research_export_title(job)
    cover_data = {
        "document_type": "Deep Research Report",
        "document_id": job.id,
        "classification": classification,
        "prepared_by": prepared_by or "",
    }

    if format == "docx":
        from keprix.research_workspace.reports.pandoc import render_with_pandoc

        render = render_with_pandoc(markdown, output_format="docx")
        if render.output_path:
            path = Path(render.output_path)
            return {
                "format": "docx",
                "content": path.read_bytes(),
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "filename": research_export_filename(job, "docx"),
                "renderer": "pandoc",
            }
        return {
            "format": "markdown",
            "content": markdown.encode("utf-8"),
            "mime": "text/markdown",
            "filename": research_export_filename(job, "md"),
            "format_returned": "markdown",
            "setup_instructions": render.setup_instructions,
            "renderer": "markdown-fallback",
        }

    if format == "html":
        html_doc = markdown_to_html(markdown, title=title, template="research")
        if include_cover:
            from keprix.export.cover_page import generate_cover_html
            from keprix.export.renderer import _inject_after_body_open

            cover_html = generate_cover_html(title=title, **cover_data)
            html_doc = _inject_after_body_open(html_doc, cover_html)
        return {
            "format": "html",
            "content": html_doc,
            "mime": "text/html",
            "filename": research_export_filename(job, "html"),
            "renderer": "html",
        }

    result = export_document(
        title=title,
        content=markdown,
        format=format,
        include_cover=include_cover,
        cover_data=cover_data,
        html_template="research",
    )
    fmt_returned = result.get("format_returned", result["format"])
    filename = research_export_filename(job, fmt_returned if fmt_returned != "markdown" else "md")
    payload: dict[str, Any] = {
        "format": result["format"],
        "content": result["content"],
        "mime": result["mime"],
        "filename": filename,
    }
    if "format_returned" in result:
        payload["format_returned"] = result["format_returned"]
    if "setup_instructions" in result:
        payload["setup_instructions"] = result["setup_instructions"]
    if "renderer" in result:
        payload["renderer"] = result["renderer"]
    return payload

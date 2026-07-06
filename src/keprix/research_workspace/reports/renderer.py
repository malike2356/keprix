"""Markdown report renderer."""

from __future__ import annotations

from typing import Any

from keprix.research_workspace.citations.registry import CitationLibrary
from keprix.research_workspace.reports.bibliography import render_report_bibliography
from keprix.research_workspace.reports.schemas import OutputFormat, RenderResult, ReportOutline


def _evidence_links(outline: ReportOutline, claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for claim in claims:
        links.append(
            {
                "claim_id": claim.get("claim_id"),
                "text": claim.get("text"),
                "source_id": claim.get("source_id"),
                "approved": bool(claim.get("approved")),
            }
        )
    return links


def render_markdown(
    store: Any,
    outline: ReportOutline,
    *,
    claims: list[dict[str, Any]] | None = None,
) -> RenderResult:
    citations = CitationLibrary(store).list_cached(outline.project_id)
    if claims is None:
        from keprix.research_workspace.reports.outline import _list_claims

        claims = _list_claims(store, outline.project_id)

    lines = [
        f"# {outline.title}",
        "",
        f"_Report type: {outline.report_type}_",
        "",
    ]
    if outline.question:
        lines.extend([f"**Research question:** {outline.question}", ""])

    for section in outline.sections:
        lines.append(f"## {section.heading}")
        lines.append("")
        lines.append(section.body.strip())
        lines.append("")

    lines.append("## Evidence map")
    lines.append("")
    evidence_links = _evidence_links(outline, claims)
    if evidence_links:
        for item in evidence_links:
            source = item.get("source_id") or "unlinked"
            lines.append(f"- `{item.get('claim_id')}` -> `{source}`: {item.get('text')}")
    else:
        lines.append("_No claims available for evidence mapping._")
    lines.append("")

    lines.append(render_report_bibliography(citations).rstrip())
    lines.append("")

    markdown = "\n".join(lines).strip() + "\n"
    return RenderResult(
        format="markdown",
        markdown=markdown,
        renderer="markdown",
        citation_keys=[record.citation_key for record in citations],
        evidence_links=evidence_links,
    )


def render_report(
    store: Any,
    outline: ReportOutline,
    *,
    output_format: OutputFormat = "markdown",
    workdir: Any | None = None,
    claims: list[dict[str, Any]] | None = None,
) -> RenderResult:
    base = render_markdown(store, outline, claims=claims)
    if output_format == "markdown":
        return base

    from keprix.research_workspace.reports.pandoc import render_with_pandoc

    return render_with_pandoc(
        base.markdown,
        output_format=output_format,
        workdir=workdir,
        citation_keys=base.citation_keys,
        evidence_links=base.evidence_links,
    )

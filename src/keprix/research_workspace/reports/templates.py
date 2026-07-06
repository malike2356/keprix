"""Section templates per report type."""

from __future__ import annotations

from keprix.research_workspace.reports.schemas import ReportSection, ReportType

_SECTION_ORDER: dict[ReportType, list[str]] = {
    "literature_review": ["summary", "sources", "claims", "synthesis"],
    "methods_results": ["methods", "results", "claims"],
    "survey_analysis": ["overview", "dataset", "findings", "claims"],
    "market_research": ["overview", "findings", "claims"],
    "policy_brief": ["summary", "findings", "claims", "recommendations"],
    "field_research": ["overview", "field_context", "findings", "claims"],
    "evidence_appendix": ["claims", "sources"],
    "client_pdf": ["summary", "findings", "claims", "sources"],
}

_DEFAULT_TITLES: dict[ReportType, str] = {
    "literature_review": "Literature Review",
    "methods_results": "Methods and Results",
    "survey_analysis": "Survey Analysis Report",
    "market_research": "Market Research Report",
    "policy_brief": "Policy Brief",
    "field_research": "Field Research Report",
    "evidence_appendix": "Evidence Appendix",
    "client_pdf": "Research Report",
}


def default_title(report_type: ReportType) -> str:
    return _DEFAULT_TITLES.get(report_type, "Research Report")


def section_order(report_type: ReportType) -> list[str]:
    return list(_SECTION_ORDER.get(report_type, ["summary", "findings", "claims"]))


def build_section(
    key: str,
    *,
    project_title: str,
    question: str | None,
    sources: list[dict],
    claims: list[dict],
    datasets: list[dict],
) -> ReportSection:
    if key == "summary":
        body = f"This report summarizes work for **{project_title}**."
        if question:
            body += f"\n\nResearch question: {question}"
        return ReportSection(heading="Executive Summary", body=body)

    if key == "overview":
        return ReportSection(
            heading="Overview",
            body=f"Project: {project_title}\n\nThis section introduces the analysis scope and inputs.",
        )

    if key == "sources":
        lines = ["The following sources were registered for this project:", ""]
        for source in sources:
            lines.append(f"- `{source.get('source_id')}` ({source.get('kind')}): {source.get('ref')}")
        if not sources:
            lines.append("_No sources registered yet._")
        return ReportSection(
            heading="Sources",
            body="\n".join(lines),
            source_refs=[str(s.get("source_id")) for s in sources if s.get("source_id")],
        )

    if key == "claims":
        lines = ["Recorded claims for this project:", ""]
        for claim in claims:
            approved = "approved" if claim.get("approved") else "pending review"
            source_id = claim.get("source_id")
            suffix = f" (source: `{source_id}`)" if source_id else " (no source linked)"
            lines.append(f"- [{approved}] {claim.get('text')}{suffix}")
        if not claims:
            lines.append("_No claims recorded yet._")
        return ReportSection(
            heading="Findings",
            body="\n".join(lines),
            source_refs=[str(c.get("source_id")) for c in claims if c.get("source_id")],
        )

    if key == "dataset":
        lines = ["Registered datasets:", ""]
        for dataset in datasets:
            lines.append(
                f"- `{dataset.get('object_id')}`: {dataset.get('payload', {}).get('name', 'dataset')}"
            )
        if not datasets:
            lines.append("_No datasets registered yet._")
        return ReportSection(heading="Dataset", body="\n".join(lines))

    if key == "findings":
        approved = [c for c in claims if c.get("approved")]
        body = "\n".join(f"- {item.get('text')}" for item in approved) or "_No approved findings yet._"
        return ReportSection(heading="Key Findings", body=body)

    if key == "methods":
        return ReportSection(
            heading="Methods",
            body="Methods are derived from registered datasets, analysis runs, and playbook steps.",
        )

    if key == "results":
        return ReportSection(
            heading="Results",
            body="Results summarize statistical outputs and approved claims linked to sources.",
        )

    if key == "synthesis":
        return ReportSection(
            heading="Synthesis",
            body="Synthesis combines extracted claims and cited sources into a coherent narrative.",
        )

    if key == "recommendations":
        return ReportSection(
            heading="Recommendations",
            body="Recommendations should be confirmed by a human reviewer before external release.",
        )

    if key == "field_context":
        return ReportSection(
            heading="Field Context",
            body="Operational context for borehole drilling, community water access, and compliance checks.",
        )

    return ReportSection(heading=key.replace("_", " ").title(), body="")

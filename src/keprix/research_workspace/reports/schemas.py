"""Typed models for research report generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ReportType = Literal[
    "literature_review",
    "methods_results",
    "survey_analysis",
    "market_research",
    "policy_brief",
    "field_research",
    "evidence_appendix",
    "client_pdf",
]

OutputFormat = Literal["markdown", "html", "pdf", "docx"]


@dataclass
class ReportSection:
    heading: str
    body: str
    source_refs: list[str] = field(default_factory=list)


@dataclass
class ReportOutline:
    project_id: str
    title: str
    question: str | None
    report_type: ReportType
    sections: list[ReportSection] = field(default_factory=list)
    citation_keys: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "question": self.question,
            "report_type": self.report_type,
            "sections": [
                {
                    "heading": section.heading,
                    "body": section.body,
                    "source_refs": section.source_refs,
                }
                for section in self.sections
            ],
            "citation_keys": self.citation_keys,
            "claim_ids": self.claim_ids,
            "source_ids": self.source_ids,
            "artifact_ids": self.artifact_ids,
        }


@dataclass
class RenderResult:
    format: OutputFormat
    markdown: str
    output_path: str | None = None
    renderer: str = "markdown"
    setup_instructions: str | None = None
    citation_keys: list[str] = field(default_factory=list)
    evidence_links: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "markdown": self.markdown,
            "output_path": self.output_path,
            "renderer": self.renderer,
            "setup_instructions": self.setup_instructions,
            "citation_keys": self.citation_keys,
            "evidence_links": self.evidence_links,
        }

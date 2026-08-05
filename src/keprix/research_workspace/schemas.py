"""Canonical research workspace schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from keprix.compat import StrEnum
from typing import Any
from uuid import uuid4


class SensitivityLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class ExportPolicy(StrEnum):
    ALLOW = "allow"
    REDACT = "redact"
    DENY = "deny"


class ResearchObjectType(StrEnum):
    PROJECT = "research_project"
    SOURCE = "source"
    CITATION = "citation"
    NOTE = "note"
    CLAIM = "claim"
    DATASET = "dataset"
    CODEBOOK = "codebook"
    ANALYSIS_RUN = "analysis_run"
    STATISTICAL_OUTPUT = "statistical_output"
    FIGURE = "figure"
    REPORT = "report"
    EVIDENCE_BUNDLE = "evidence_bundle"


@dataclass
class ResearchObjectBase:
    workspace_id: str
    project_id: str
    owner: str
    source_ref: str | None
    provenance: dict[str, Any]
    created_at: str
    updated_at: str
    trace_id: str
    sensitivity_level: str
    export_policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_trace_id() -> str:
    return str(uuid4())


@dataclass
class ResearchProject(ResearchObjectBase):
    project_id: str
    title: str
    question: str | None = None
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "object_type": ResearchObjectType.PROJECT.value,
                "project_id": self.project_id,
                "title": self.title,
                "question": self.question,
                "status": self.status,
            }
        )
        return data


@dataclass
class ResearchSource(ResearchObjectBase):
    source_id: str
    kind: str
    ref: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "object_type": ResearchObjectType.SOURCE.value,
                "source_id": self.source_id,
                "kind": self.kind,
                "ref": self.ref,
                "metadata": self.metadata,
            }
        )
        return data


@dataclass
class ResearchNote(ResearchObjectBase):
    note_id: str
    title: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "object_type": ResearchObjectType.NOTE.value,
                "note_id": self.note_id,
                "title": self.title,
                "body": self.body,
            }
        )
        return data


@dataclass
class ResearchClaim(ResearchObjectBase):
    claim_id: str
    text: str
    source_id: str | None = None
    confidence: float | None = None
    approved: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "object_type": ResearchObjectType.CLAIM.value,
                "claim_id": self.claim_id,
                "text": self.text,
                "source_id": self.source_id,
                "confidence": self.confidence,
                "approved": self.approved,
            }
        )
        return data


@dataclass
class ResearchDataset(ResearchObjectBase):
    dataset_id: str
    name: str
    format: str
    path: str
    engine: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "object_type": ResearchObjectType.DATASET.value,
                "dataset_id": self.dataset_id,
                "name": self.name,
                "format": self.format,
                "path": self.path,
                "engine": self.engine,
            }
        )
        return data


@dataclass
class AnalysisRun(ResearchObjectBase):
    run_id: str
    tool: str
    status: str
    job_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "object_type": ResearchObjectType.ANALYSIS_RUN.value,
                "run_id": self.run_id,
                "tool": self.tool,
                "status": self.status,
                "job_id": self.job_id,
                "parameters": self.parameters,
            }
        )
        return data


@dataclass
class EvidenceBundle(ResearchObjectBase):
    bundle_id: str
    label: str
    members: list[str]
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "object_type": ResearchObjectType.EVIDENCE_BUNDLE.value,
                "bundle_id": self.bundle_id,
                "label": self.label,
                "members": self.members,
                "summary": self.summary,
            }
        )
        return data


EXTERNAL_TOOL_OWNERS = frozenset(
    {
        "obsidian",
        "zotero",
        "pspp",
        "jamovi",
        "r",
        "python",
        "jupyter",
        "pandoc",
        "quarto",
    }
)

KEPRIX_OWNED_CAPABILITIES = frozenset(
    {
        "project_orchestration",
        "source_ingestion",
        "evidence_tracking",
        "agent_analysis",
        "playbook_execution",
        "artifact_store",
        "report_assembly",
        "audit_trail",
    }
)

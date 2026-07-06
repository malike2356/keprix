"""Enhanced evidence bundle export for reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.research_workspace.citations.registry import CitationLibrary
from keprix.research_workspace.evidence import EvidenceService
from keprix.research_workspace.reports.outline import _list_claims, _list_sources


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceExportPackage:
    project_id: str
    bundle_id: str | None
    label: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    datasets: list[dict[str, Any]] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    claim_evidence_map: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    trace_log: list[dict[str, Any]] = field(default_factory=list)
    exported_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "bundle_id": self.bundle_id,
            "label": self.label,
            "sources": self.sources,
            "citations": self.citations,
            "datasets": self.datasets,
            "claims": self.claims,
            "claim_evidence_map": self.claim_evidence_map,
            "artifacts": self.artifacts,
            "trace_log": self.trace_log,
            "exported_at": self.exported_at,
        }


def _claim_evidence_map(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping: list[dict[str, Any]] = []
    for claim in claims:
        mapping.append(
            {
                "claim_id": claim.get("claim_id"),
                "text": claim.get("text"),
                "source_id": claim.get("source_id"),
                "approved": bool(claim.get("approved")),
                "confidence": claim.get("confidence"),
                "trace_id": claim.get("trace_id"),
            }
        )
    return mapping


def _trace_log(store: Any, project_id: str, object_ids: list[str]) -> list[dict[str, Any]]:
    evidence = EvidenceService(store)
    entries: list[dict[str, Any]] = []
    for object_id in object_ids:
        try:
            chain = evidence.trace_lineage(project_id, object_id)
        except Exception:
            continue
        entries.append({"object_id": object_id, "lineage": chain})
    return entries


class EvidenceBundleExporter:
    def __init__(self, store: Any) -> None:
        self.store = store

    def build_export_package(
        self,
        project_id: str,
        *,
        label: str,
        bundle_id: str | None = None,
        member_object_ids: list[str] | None = None,
    ) -> EvidenceExportPackage:
        project = self.store.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        sources = _list_sources(self.store, project_id)
        claims = _list_claims(self.store, project_id)
        citations = [record.to_dict() for record in CitationLibrary(self.store).list_cached(project_id)]
        datasets = [
            item
            for item in self.store.list_objects(project_id, object_type="dataset")
        ]
        artifacts = self.store.list_objects(project_id)
        member_ids = member_object_ids or [item.get("object_id") for item in artifacts if item.get("object_id")]

        return EvidenceExportPackage(
            project_id=project_id,
            bundle_id=bundle_id,
            label=label,
            sources=sources,
            citations=citations,
            datasets=datasets,
            claims=claims,
            claim_evidence_map=_claim_evidence_map(claims),
            artifacts=artifacts,
            trace_log=_trace_log(self.store, project_id, [str(item) for item in member_ids if item]),
        )

    def write_package(
        self,
        project_id: str,
        *,
        label: str,
        output_dir: Path,
        bundle_id: str | None = None,
        member_object_ids: list[str] | None = None,
    ) -> Path:
        package = self.build_export_package(
            project_id,
            label=label,
            bundle_id=bundle_id,
            member_object_ids=member_object_ids,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "evidence-bundle.json"
        out_path.write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
        return out_path

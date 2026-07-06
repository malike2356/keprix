"""Evidence bundles and provenance lineage."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.research_workspace.errors import ProvenanceError
from keprix.research_workspace.schemas import EvidenceBundle, ExportPolicy, SensitivityLevel, new_trace_id


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def add_claim(
        self,
        project_id: str,
        *,
        text: str,
        source_id: str | None,
        owner: str,
        confidence: float | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        if source_id and not self.store.get_source(project_id, source_id):
            raise ProvenanceError(f"Source {source_id} is not registered for project {project_id}")
        return self.store.add_claim(
            project_id,
            text=text,
            source_id=source_id,
            confidence=confidence,
            approved=approved,
            owner=owner,
            trace_id=new_trace_id(),
        )

    def build_bundle(
        self,
        project_id: str,
        *,
        label: str,
        owner: str,
        member_object_ids: list[str] | None = None,
        summary: str = "",
    ) -> EvidenceBundle:
        members = member_object_ids or self._default_members(project_id)
        if not members:
            raise ProvenanceError("Evidence bundle requires at least one traced member")
        bundle_id = f"evb-{uuid.uuid4().hex[:10]}"
        trace_id = new_trace_id()
        row = self.store.save_object(
            object_id=bundle_id,
            object_type="evidence_bundle",
            project_id=project_id,
            owner=owner,
            source_ref=None,
            provenance={"members": members},
            payload={"label": label, "summary": summary, "members": members},
            trace_id=trace_id,
        )
        project = self.store.get_project(project_id) or {}
        return EvidenceBundle(
            workspace_id=project.get("workspace_id") or self.store.plane.workspace_id,
            project_id=project_id,
            owner=owner,
            source_ref=None,
            provenance={"members": members},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            trace_id=trace_id,
            sensitivity_level=row.get("sensitivity_level") or SensitivityLevel.INTERNAL.value,
            export_policy=row.get("export_policy") or ExportPolicy.ALLOW.value,
            bundle_id=bundle_id,
            label=label,
            members=members,
            summary=summary,
        )

    def trace_lineage(self, project_id: str, object_id: str) -> list[dict[str, Any]]:
        chain = self.store.lineage_chain(project_id, object_id)
        if not chain:
            raise ProvenanceError(f"No lineage found for {object_id}")
        return chain

    def _default_members(self, project_id: str) -> list[str]:
        members: list[str] = []
        with self.store.plane.connect() as conn:
            sources = conn.execute(
                "SELECT source_id FROM research_sources WHERE project_id = ?",
                (project_id,),
            ).fetchall()
            claims = conn.execute(
                "SELECT claim_id, source_id FROM research_claims WHERE project_id = ?",
                (project_id,),
            ).fetchall()
        members.extend(row["source_id"] for row in sources)
        members.extend(row["claim_id"] for row in claims)
        return members

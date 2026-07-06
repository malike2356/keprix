"""Provenance-first research workspace store."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.data_architecture.data_plane import get_workspace_data_plane
from keprix.jobs.queue import JobQueue


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchWorkspaceStore:
    def __init__(self, workspace_id: str = "default") -> None:
        self.plane = get_workspace_data_plane(workspace_id)
        self.plane.initialize()

    def create_project(
        self,
        *,
        title: str,
        question: str | None = None,
        owner: str = "default",
        trace_id: str | None = None,
        sensitivity_level: str = "internal",
        export_policy: str = "allow",
    ) -> dict[str, Any]:
        project_id = f"rp-{uuid.uuid4().hex[:10]}"
        now = _utcnow()
        trace = trace_id or str(uuid.uuid4())
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO research_projects (
                    project_id, workspace_id, title, question, status,
                    created_at, updated_at, owner, trace_id,
                    sensitivity_level, export_policy, provenance_json
                )
                VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    self.plane.workspace_id,
                    title,
                    question,
                    now,
                    now,
                    owner,
                    trace,
                    sensitivity_level,
                    export_policy,
                    json.dumps({"created_by": owner}),
                ),
            )
        return self.get_project(project_id) or {"project_id": project_id, "title": title}

    def list_projects(self) -> list[dict[str, Any]]:
        with self.plane.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM research_projects ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.plane.connect() as conn:
            row = conn.execute(
                "SELECT * FROM research_projects WHERE project_id = ?", (project_id,)
            ).fetchone()
        return dict(row) if row else None

    def add_source(
        self,
        project_id: str,
        *,
        kind: str,
        ref: str,
        metadata: dict[str, Any] | None = None,
        owner: str = "default",
        trace_id: str | None = None,
        sensitivity_level: str = "internal",
        export_policy: str = "allow",
    ) -> dict[str, Any]:
        source_id = f"src-{uuid.uuid4().hex[:10]}"
        trace = trace_id or str(uuid.uuid4())
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO research_sources (
                    source_id, project_id, kind, ref, retrieved_at, metadata_json,
                    owner, trace_id, sensitivity_level, export_policy
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    project_id,
                    kind,
                    ref,
                    now,
                    json.dumps(metadata or {}),
                    owner,
                    trace,
                    sensitivity_level,
                    export_policy,
                ),
            )
        self.save_object(
            object_id=source_id,
            object_type="source",
            project_id=project_id,
            owner=owner,
            source_ref=ref,
            provenance={"kind": kind},
            payload={"kind": kind, "ref": ref, "metadata": metadata or {}},
            trace_id=trace,
            sensitivity_level=sensitivity_level,
            export_policy=export_policy,
        )
        return {"source_id": source_id, "project_id": project_id, "kind": kind, "ref": ref}

    def get_source(self, project_id: str, source_id: str) -> dict[str, Any] | None:
        with self.plane.connect() as conn:
            row = conn.execute(
                "SELECT * FROM research_sources WHERE project_id = ? AND source_id = ?",
                (project_id, source_id),
            ).fetchone()
        return dict(row) if row else None

    def add_claim(
        self,
        project_id: str,
        *,
        text: str,
        source_id: str | None = None,
        confidence: float | None = None,
        approved: bool = False,
        owner: str = "default",
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        claim_id = f"clm-{uuid.uuid4().hex[:10]}"
        trace = trace_id or str(uuid.uuid4())
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO research_claims (
                    claim_id, project_id, source_id, text, confidence, approved, created_at,
                    owner, trace_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim_id,
                    project_id,
                    source_id,
                    text,
                    confidence,
                    1 if approved else 0,
                    now,
                    owner,
                    trace,
                ),
            )
        self.save_object(
            object_id=claim_id,
            object_type="claim",
            project_id=project_id,
            owner=owner,
            source_ref=source_id,
            provenance={"source_id": source_id},
            payload={"text": text, "confidence": confidence, "approved": approved},
            trace_id=trace,
        )
        return {"claim_id": claim_id, "project_id": project_id, "source_id": source_id, "text": text}

    def list_citations(self, project_id: str) -> list[dict[str, Any]]:
        with self.plane.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM research_citations WHERE project_id = ? ORDER BY citation_id",
                (project_id,),
            ).fetchall()
        return [
            {
                "citation_id": row["citation_id"],
                "project_id": row["project_id"],
                "source_id": row["source_id"],
                "label": row["label"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
            for row in rows
        ]

    def add_citation(
        self,
        project_id: str,
        *,
        label: str,
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        citation_id = f"cite-{uuid.uuid4().hex[:10]}"
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO research_citations (citation_id, project_id, source_id, label, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (citation_id, project_id, source_id, label, json.dumps(metadata or {})),
            )
        return {"citation_id": citation_id, "label": label, "source_id": source_id}

    def save_object(
        self,
        *,
        object_id: str,
        object_type: str,
        project_id: str,
        owner: str,
        source_ref: str | None,
        provenance: dict[str, Any],
        payload: dict[str, Any],
        trace_id: str,
        sensitivity_level: str = "internal",
        export_policy: str = "allow",
    ) -> dict[str, Any]:
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO research_objects (
                    object_id, object_type, workspace_id, project_id, owner, source_ref,
                    provenance_json, payload_json, trace_id, sensitivity_level, export_policy,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(object_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    provenance_json = excluded.provenance_json,
                    updated_at = excluded.updated_at
                """,
                (
                    object_id,
                    object_type,
                    self.plane.workspace_id,
                    project_id,
                    owner,
                    source_ref,
                    json.dumps(provenance),
                    json.dumps(payload),
                    trace_id,
                    sensitivity_level,
                    export_policy,
                    now,
                    now,
                ),
            )
        return {
            "object_id": object_id,
            "object_type": object_type,
            "project_id": project_id,
            "trace_id": trace_id,
            "created_at": now,
            "updated_at": now,
            "sensitivity_level": sensitivity_level,
            "export_policy": export_policy,
        }

    def list_objects(self, project_id: str, object_type: str | None = None) -> list[dict[str, Any]]:
        with self.plane.connect() as conn:
            if object_type:
                rows = conn.execute(
                    """
                    SELECT * FROM research_objects
                    WHERE project_id = ? AND object_type = ?
                    ORDER BY created_at DESC
                    """,
                    (project_id, object_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM research_objects WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,),
                ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["provenance"] = json.loads(item.pop("provenance_json") or "{}")
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            results.append(item)
        return results

    def lineage_chain(self, project_id: str, object_id: str) -> list[dict[str, Any]]:
        chain: list[dict[str, Any]] = []
        with self.plane.connect() as conn:
            row = conn.execute(
                "SELECT * FROM research_objects WHERE project_id = ? AND object_id = ?",
                (project_id, object_id),
            ).fetchone()
            if row:
                current = dict(row)
                current["provenance"] = json.loads(current.pop("provenance_json") or "{}")
                current["payload"] = json.loads(current.pop("payload_json") or "{}")
                chain.append(current)
                source_ref = current.get("source_ref")
                if source_ref:
                    source = conn.execute(
                        "SELECT * FROM research_sources WHERE project_id = ? AND source_id = ?",
                        (project_id, source_ref),
                    ).fetchone()
                    if source:
                        chain.append({"object_type": "source", **dict(source)})
                members = current.get("provenance", {}).get("members") or []
                for member_id in members:
                    member = conn.execute(
                        "SELECT * FROM research_objects WHERE project_id = ? AND object_id = ?",
                        (project_id, member_id),
                    ).fetchone()
                    if member:
                        entry = dict(member)
                        entry["provenance"] = json.loads(entry.pop("provenance_json") or "{}")
                        entry["payload"] = json.loads(entry.pop("payload_json") or "{}")
                        chain.append(entry)
            else:
                source = conn.execute(
                    "SELECT * FROM research_sources WHERE project_id = ? AND source_id = ?",
                    (project_id, object_id),
                ).fetchone()
                if source:
                    chain.append({"object_type": "source", **dict(source)})
                claim = conn.execute(
                    "SELECT * FROM research_claims WHERE project_id = ? AND claim_id = ?",
                    (project_id, object_id),
                ).fetchone()
                if claim:
                    item = dict(claim)
                    if item.get("source_id"):
                        parent = conn.execute(
                            "SELECT * FROM research_sources WHERE source_id = ?",
                            (item["source_id"],),
                        ).fetchone()
                        if parent:
                            chain.append({"object_type": "source", **dict(parent)})
                    chain.append({"object_type": "claim", **item})
        return chain

    def enqueue_research_job(self, *, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        queue = JobQueue(self.plane.workspace_id)
        queue.plane = self.plane
        return queue.enqueue(job_type, payload)


_store: dict[str, ResearchWorkspaceStore] = {}


def get_research_workspace_store(workspace_id: str = "default") -> ResearchWorkspaceStore:
    if workspace_id not in _store:
        _store[workspace_id] = ResearchWorkspaceStore(workspace_id)
    return _store[workspace_id]

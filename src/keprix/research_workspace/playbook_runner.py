"""Research workspace YAML playbook loader and runner."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from keprix.research_workspace.schemas import new_trace_id

PLAYBOOK_DIR = Path(__file__).resolve().parent / "playbooks"


@dataclass
class StepResult:
    step_id: str
    title: str
    action: str
    status: str
    artifact_id: str | None = None
    artifact_type: str | None = None
    needs_human_review: bool = False
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "action": self.action,
            "status": self.status,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "needs_human_review": self.needs_human_review,
            "message": self.message,
            "payload": self.payload,
        }


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_playbook_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for path in sorted(PLAYBOOK_DIR.glob("*.yaml")):
        spec = load_playbook_file(path)
        specs.append(
            {
                "id": spec["id"],
                "name": spec.get("name") or spec["id"],
                "description": spec.get("description") or "",
                "domain": spec.get("domain") or "generic",
                "step_count": len(spec.get("steps") or []),
            }
        )
    return specs


def load_playbook(playbook_id: str) -> dict[str, Any]:
    path = PLAYBOOK_DIR / f"{playbook_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown research playbook: {playbook_id}")
    return load_playbook_file(path)


def load_playbook_file(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("id"):
        data["id"] = path.stem
    return data


def _artifact(
    store: Any,
    *,
    project_id: str,
    owner: str,
    trace_id: str,
    object_type: str,
    object_id: str,
    payload: dict[str, Any],
    provenance: dict[str, Any],
) -> str:
    store.save_object(
        object_id=object_id,
        object_type=object_type,
        project_id=project_id,
        owner=owner,
        source_ref=payload.get("path"),
        provenance=provenance,
        payload=payload,
        trace_id=trace_id,
    )
    return object_id


def _dry_step(step: dict[str, Any], *, trace_id: str) -> StepResult:
    step_id = str(step["id"])
    requires_review = bool(step.get("requires_review")) or step.get("risk") == "high"
    artifact_id = f"art-{uuid.uuid4().hex[:10]}"
    return StepResult(
        step_id=step_id,
        title=str(step.get("title") or step_id),
        action=str(step.get("action") or "noop"),
        status="dry_run",
        artifact_id=artifact_id,
        artifact_type=str(step.get("action") or "artifact").split(".")[0],
        needs_human_review=requires_review,
        message="Dry run completed",
        payload={"trace_id": trace_id, "fixture": True},
    )


def _handler_zotero_import(ctx: dict[str, Any], step: dict[str, Any]) -> StepResult:
    store = ctx["store"]
    project_id = ctx["project_id"]
    owner = ctx["owner"]
    trace_id = ctx["trace_id"]
    artifact_id = f"zot-{uuid.uuid4().hex[:8]}"
    _artifact(
        store,
        project_id=project_id,
        owner=owner,
        trace_id=trace_id,
        object_type="citation_import",
        object_id=artifact_id,
        payload={"collection": ctx.get("zotero_collection") or "default", "imported": 1},
        provenance={"playbook": ctx["playbook_id"], "step": step["id"]},
    )
    return StepResult(
        step_id=step["id"],
        title=step.get("title", step["id"]),
        action=step["action"],
        status="completed",
        artifact_id=artifact_id,
        artifact_type="citation_import",
        message="Zotero collection import queued",
    )


def _handler_claims(ctx: dict[str, Any], step: dict[str, Any]) -> StepResult:
    store = ctx["store"]
    evidence = ctx["evidence"]
    project_id = ctx["project_id"]
    claim = evidence.add_claim(
        project_id,
        text=ctx.get("claim_text") or "Imported claim from literature review playbook.",
        source_id=None,
        owner=ctx["owner"],
        confidence=0.6,
        approved=False,
    )
    return StepResult(
        step_id=step["id"],
        title=step.get("title", step["id"]),
        action=step["action"],
        status="completed",
        artifact_id=str(claim.get("claim_id") or claim.get("id")),
        artifact_type="claim",
        needs_human_review=True,
        message="Claim extracted; pending review",
        payload=claim,
    )


def _handler_dataset(ctx: dict[str, Any], step: dict[str, Any]) -> StepResult:
    artifacts = ctx["artifacts"]
    project_id = ctx["project_id"]
    dataset_path = ctx.get("dataset_path")
    if dataset_path:
        from pathlib import Path as PathLib

        imported = ctx["dataset_manager"].import_file(
            project_id,
            source_path=PathLib(dataset_path),
            name=ctx.get("dataset_name") or "Survey",
            owner=ctx["owner"],
        )
        dataset_id = imported["dataset_id"]
    else:
        registered = artifacts.register_dataset(
            project_id,
            name=ctx.get("dataset_name") or "Fixture dataset",
            path=str(ctx.get("fixture_dataset") or "fixtures/survey.csv"),
            format="csv",
            owner=ctx["owner"],
        )
        dataset_id = registered.dataset_id
    artifact_id = dataset_id
    return StepResult(
        step_id=step["id"],
        title=step.get("title", step["id"]),
        action=step["action"],
        status="completed",
        artifact_id=artifact_id,
        artifact_type="dataset",
        message="Dataset registered",
    )


_REPORT_ACTION_TYPES: dict[str, str] = {
    "report.generate": "survey_analysis",
    "report.draft_literature_review": "literature_review",
    "report.operational_insight": "field_research",
}


def _handler_report(ctx: dict[str, Any], step: dict[str, Any]) -> StepResult:
    from keprix.research_workspace.reports.report import ReportService

    action = str(step.get("action") or "")
    report_type = str(ctx.get("report_type") or _REPORT_ACTION_TYPES.get(action) or "client_pdf")
    requires_review = bool(step.get("requires_review")) or step.get("risk") == "high"
    result = ReportService(ctx["store"]).generate(
        ctx["project_id"],
        report_type=report_type,  # type: ignore[arg-type]
        owner=ctx["owner"],
        title=ctx.get("report_title"),
        output_format=str(ctx.get("report_format") or "markdown"),  # type: ignore[arg-type]
        approved_claims_only=bool(ctx.get("approved_claims_only")),
        include_evidence_bundle=ctx.get("include_evidence_bundle", True) is not False,
    )
    render = result["render"]
    return StepResult(
        step_id=step["id"],
        title=step.get("title", step["id"]),
        action=action,
        status="completed",
        artifact_id=result["report_id"],
        artifact_type="report",
        needs_human_review=requires_review,
        message="Report generated",
        payload={
            "report_id": result["report_id"],
            "report_type": report_type,
            "renderer": render.get("renderer"),
            "format": render.get("format"),
            "setup_instructions": render.get("setup_instructions"),
            "citation_keys": render.get("citation_keys"),
            "evidence_links": render.get("evidence_links"),
            "evidence_bundle": result.get("evidence_bundle"),
        },
    )


def _handler_generic_artifact(ctx: dict[str, Any], step: dict[str, Any]) -> StepResult:
    store = ctx["store"]
    artifact_id = f"art-{uuid.uuid4().hex[:10]}"
    requires_review = bool(step.get("requires_review")) or step.get("risk") == "high"
    object_type = str(step.get("action") or "artifact").replace(".", "_")
    payload = {
        "playbook_id": ctx["playbook_id"],
        "step_id": step["id"],
        "summary": step.get("title") or step["id"],
        "needs_human_review": requires_review,
    }
    _artifact(
        store,
        project_id=ctx["project_id"],
        owner=ctx["owner"],
        trace_id=ctx["trace_id"],
        object_type=object_type,
        object_id=artifact_id,
        payload=payload,
        provenance={"playbook": ctx["playbook_id"], "step": step["id"], "action": step["action"]},
    )
    return StepResult(
        step_id=step["id"],
        title=step.get("title", step["id"]),
        action=step["action"],
        status="completed",
        artifact_id=artifact_id,
        artifact_type=object_type,
        needs_human_review=requires_review,
        message="Artifact recorded",
        payload=payload,
    )


HANDLERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], StepResult]] = {
    "zotero.import_collection": _handler_zotero_import,
    "citations.extract_claims": _handler_claims,
    "dataset.import": _handler_dataset,
    "dataset.prepare": _handler_dataset,
    "dataset.codebook": _handler_generic_artifact,
    "report.generate": _handler_report,
    "report.draft_literature_review": _handler_report,
    "report.operational_insight": _handler_report,
}


def execute_step(ctx: dict[str, Any], step: dict[str, Any], *, dry_run: bool) -> StepResult:
    if dry_run:
        return _dry_step(step, trace_id=ctx["trace_id"])
    action = str(step.get("action") or "")
    handler = HANDLERS.get(action, _handler_generic_artifact)
    result = handler(ctx, step)
    if bool(step.get("requires_review")) or step.get("risk") == "high":
        result.needs_human_review = True
    return result


class ResearchPlaybookRunner:
    def __init__(self, store: Any) -> None:
        self.store = store
        from keprix.research_workspace.artifact import ArtifactService
        from keprix.research_workspace.datasets.dataset import DatasetManager
        from keprix.research_workspace.evidence import EvidenceService

        self._artifacts = ArtifactService(store)
        self._evidence = EvidenceService(store)
        self._datasets = DatasetManager(store)

    def run(
        self,
        project_id: str,
        playbook_id: str,
        *,
        owner: str,
        dry_run: bool = False,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.store.get_project(project_id) is None:
            raise ValueError(f"Project not found: {project_id}")
        spec = load_playbook(playbook_id)
        trace_id = new_trace_id()
        run_id = f"rpb-{uuid.uuid4().hex[:10]}"
        params = parameters or {}
        ctx: dict[str, Any] = {
            "store": self.store,
            "artifacts": self._artifacts,
            "evidence": self._evidence,
            "dataset_manager": self._datasets,
            "project_id": project_id,
            "owner": owner,
            "trace_id": trace_id,
            "playbook_id": playbook_id,
            **params,
        }
        step_results: list[StepResult] = []
        pending_approvals: list[str] = []
        for step in spec.get("steps") or []:
            result = execute_step(ctx, step, dry_run=dry_run)
            step_results.append(result)
            if result.needs_human_review:
                pending_approvals.append(result.step_id)
        payload = {
            "run_id": run_id,
            "playbook_id": playbook_id,
            "playbook_name": spec.get("name") or playbook_id,
            "status": "dry_run" if dry_run else "completed",
            "dry_run": dry_run,
            "steps": [item.to_dict() for item in step_results],
            "pending_approvals": pending_approvals,
            "parameters": params,
            "finished_at": _utcnow(),
        }
        self.store.save_object(
            object_id=run_id,
            object_type="playbook_run",
            project_id=project_id,
            owner=owner,
            source_ref=playbook_id,
            provenance={"playbook_id": playbook_id, "dry_run": dry_run},
            payload=payload,
            trace_id=trace_id,
        )
        return {"trace_id": trace_id, "run": payload}

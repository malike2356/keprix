"""Mutation pipeline REST API (Prompt 151)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.keys.local_access import effective_access_level
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import MutationRecord, get_mutation_store
from keprix.mutation.tool_synthesizer import synthesize_tool
from keprix.improvement.tool_gap_detector import ToolGapProposal
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/mutation", tags=["mutation-pipeline"])


class RejectBody(BaseModel):
    reason: str = Field(default="", max_length=2000)


class SynthesizeBody(BaseModel):
    tool_name: str
    description: str
    example_task: str | None = None


def _require_admin() -> str:
    if effective_access_level() in {"developer", "admin", "owner"}:
        return "admin"
    raise HTTPException(status_code=403, detail="Admin access required")


def _record_dict(record: MutationRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "recorded_at": record.recorded_at.isoformat(),
        "workspace_id": record.workspace_id,
        "tier": record.tier,
        "trigger": record.trigger,
        "status": record.status,
        "name": record.name,
        "description": record.description,
        "approved_by": record.approved_by,
        "approved_at": record.approved_at.isoformat() if record.approved_at else None,
        "quality_score": record.quality_score,
        "use_count": record.use_count,
        "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
        "metadata": record.metadata,
        "before_value": record.before_value,
        "after_value": record.after_value,
    }


def _workspace_id() -> str:
    return "default"


@router.get("/tools")
async def list_generated_tools(
    status: str | None = None,
    tier: str | None = Query(default="tool"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    store = get_mutation_store()
    items, total = store.list_mutations(
        _workspace_id(),
        tier=tier,
        status=status,
        page=page,
        per_page=per_page,
    )
    return {
        "items": [_record_dict(item) for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/tools/{record_id}")
async def get_generated_tool(
    record_id: str,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    record = get_mutation_store().get_generated_tool(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="mutation not found")
    return _record_dict(record)


@router.get("/tools/{record_id}/source")
async def get_generated_tool_source(
    record_id: str,
    _session: str = Depends(require_developer_session),
) -> dict[str, str]:
    record = get_mutation_store().get_generated_tool(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="mutation not found")
    if not record.source_code:
        raise HTTPException(status_code=404, detail="no source code on record")
    return {"id": record.id, "name": record.name, "source_code": record.source_code}


@router.post("/tools/{record_id}/approve")
async def approve_generated_tool(
    record_id: str,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    record = get_mutation_store().approve_mutation(record_id, approved_by="api")
    if record is None:
        raise HTTPException(status_code=404, detail="mutation not found")
    return _record_dict(record)


@router.post("/tools/{record_id}/reject")
async def reject_generated_tool(
    record_id: str,
    body: RejectBody,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    record = get_mutation_store().reject_mutation(record_id, rejected_by="api", reason=body.reason)
    if record is None:
        raise HTTPException(status_code=404, detail="mutation not found")
    return _record_dict(record)


@router.post("/tools/{record_id}/rollback")
async def rollback_generated_tool(
    record_id: str,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    record = get_mutation_store().rollback_mutation(record_id, rolled_back_by="api")
    if record is None:
        raise HTTPException(status_code=404, detail="mutation not found")
    return _record_dict(record)


@router.post("/synthesize", status_code=202)
async def synthesize_tool_endpoint(
    body: SynthesizeBody,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    settings = get_mutation_settings()
    if not settings.enabled or not settings.tool_synthesis:
        raise HTTPException(status_code=503, detail="mutation tool synthesis is disabled")

    store = get_mutation_store()
    workspace_id = _workspace_id()
    proposal = ToolGapProposal(
        proposal_id="manual",
        tool_name=body.tool_name,
        description=body.description,
        confidence=settings.auto_approve_threshold,
    )
    result = await synthesize_tool(proposal, workspace_id)
    if not result.success or not result.source_code:
        raise HTTPException(status_code=422, detail=result.error or "synthesis failed")

    record = store.save_generated_tool(
        workspace_id=workspace_id,
        tool_name=result.tool_name,
        description=body.description,
        source_code=result.source_code,
        trigger="manual",
        confidence=proposal.confidence,
        auto_approve_threshold=settings.auto_approve_threshold,
    )
    if record.status == "approved":
        generated_dir = store.generated_tools_dir()
        store.write_tool_to_disk(record, generated_dir)
        store.reload_registry(generated_dir)
    return {"id": record.id, "status": record.status, "name": record.name}


@router.get("/queue")
async def mutation_queue(_admin: str = Depends(_require_admin)) -> dict[str, Any]:
    store = get_mutation_store()
    items, total = store.list_mutations(_workspace_id(), status="staged", page=1, per_page=100)
    return {"items": [_record_dict(item) for item in items], "total": total}


@router.get("/stats")
async def mutation_stats(_session: str = Depends(require_developer_session)) -> dict[str, Any]:
    store = get_mutation_store()
    workspace_id = _workspace_id()
    raw = store.mutation_stats(workspace_id)
    counts = raw.get("counts", {})
    staged = sum(tier_counts.get("staged", 0) for tier_counts in counts.values())
    active_tools = counts.get("tool", {}).get("approved", 0)
    prompt_records, _prompt_total = store.list_mutations(
        workspace_id,
        tier="prompt",
        page=1,
        per_page=1000,
    )
    evolved_prompts = len({item.name for item in prompt_records})
    code_merged = counts.get("code", {}).get("approved", 0)
    return {
        **raw,
        "staged": staged,
        "active_tools": active_tools,
        "evolved_prompts": evolved_prompts,
        "code_merged": code_merged,
    }


@router.get("/history")
async def mutation_history(
    tier: str | None = None,
    status: str | None = None,
    trigger: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    store = get_mutation_store()
    items, total = store.list_mutations(
        _workspace_id(),
        tier=tier,
        status=status,
        page=page,
        per_page=per_page,
    )
    if trigger:
        items = [item for item in items if item.trigger == trigger]
        total = len(items)
    if date_from or date_to:
        filtered = []
        for item in items:
            recorded = item.recorded_at.date().isoformat()
            if date_from and recorded < date_from:
                continue
            if date_to and recorded > date_to:
                continue
            filtered.append(item)
        items = filtered
        total = len(filtered)
    items.sort(key=lambda row: row.recorded_at, reverse=True)
    return {
        "items": [_record_dict(item) for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def _version_dict(version) -> dict[str, Any]:
    return {
        "id": version.id,
        "workspace_id": version.workspace_id,
        "prompt_key": version.prompt_key,
        "version": version.version,
        "content": version.content,
        "is_active": version.is_active,
        "created_at": version.created_at.isoformat(),
        "created_by": version.created_by,
        "mutation_id": version.mutation_id,
        "notes": version.notes,
    }


@router.get("/prompts")
async def list_prompt_versions(
    prompt_key: str | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    from keprix.mutation.prompt_store import get_prompt_store

    items, total = get_prompt_store().list_prompt_versions(
        _workspace_id(),
        prompt_key=prompt_key,
        page=page,
        per_page=per_page,
    )
    return {
        "items": [_version_dict(item) for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/prompts/{prompt_key}/history")
async def prompt_history(
    prompt_key: str,
    limit: int = Query(default=20, ge=1, le=100),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    from keprix.mutation.prompt_store import get_prompt_store

    history = get_prompt_store().get_history(_workspace_id(), prompt_key, limit=limit)
    return {"prompt_key": prompt_key, "items": [_version_dict(item) for item in history]}


@router.post("/prompts/{prompt_key}/approve")
async def approve_prompt_version(
    prompt_key: str,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    from keprix.mutation.prompt_store import get_prompt_store

    store = get_prompt_store()
    versions, _total = store.list_prompt_versions(_workspace_id(), prompt_key=prompt_key, page=1, per_page=50)
    staged = next((item for item in versions if not item.is_active), None)
    if staged is None:
        raise HTTPException(status_code=404, detail="no staged prompt version found")
    activated = store.activate_version(staged.id, activated_by="api")
    return _version_dict(activated)


@router.post("/prompts/{prompt_key}/rollback")
async def rollback_prompt_version(
    prompt_key: str,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    from keprix.mutation.prompt_store import get_prompt_store

    restored = get_prompt_store().rollback_to_previous(_workspace_id(), prompt_key, rolled_back_by="api")
    if restored is None:
        raise HTTPException(status_code=404, detail="no previous prompt version to restore")
    return _version_dict(restored)


@router.post("/prompts/versions/{version_id}/activate")
async def activate_prompt_version(
    version_id: str,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    from keprix.mutation.prompt_store import get_prompt_store

    activated = get_prompt_store().activate_version(version_id, activated_by="api")
    return _version_dict(activated)


@router.get("/personas/{persona_id}/overrides")
async def persona_overrides(
    persona_id: str,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    from keprix.mutation.persona_mutation_store import get_persona_mutation_store

    overrides = get_persona_mutation_store().get_overrides(_workspace_id(), persona_id)
    return {"persona_id": persona_id, "overrides": overrides}


class PersonaApproveBody(BaseModel):
    mutation_id: str


@router.post("/personas/{persona_id}/approve")
async def approve_persona_override(
    persona_id: str,
    body: PersonaApproveBody,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    from keprix.mutation.persona_mutation_store import get_persona_mutation_store

    record = get_persona_mutation_store().approve_override(body.mutation_id, approved_by="api")
    if record is None:
        raise HTTPException(status_code=404, detail="persona mutation not found")
    return _record_dict(record)


class PersonaRollbackBody(BaseModel):
    field: str


@router.post("/personas/{persona_id}/rollback")
async def rollback_persona_override(
    persona_id: str,
    body: PersonaRollbackBody,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    from keprix.mutation.persona_mutation_store import get_persona_mutation_store

    record = get_persona_mutation_store().rollback_override(
        _workspace_id(),
        persona_id,
        body.field,
        rolled_back_by="api",
    )
    if record is None:
        raise HTTPException(status_code=404, detail="no persona override to rollback")
    return _record_dict(record)


class CodeMutationRequestBody(BaseModel):
    task: str
    target_dir: str = "src/keprix/tools/"
    run_tests: bool = True


@router.post("/code/request", status_code=202)
async def request_code_mutation(
    body: CodeMutationRequestBody,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    settings = get_mutation_settings()
    if not settings.enabled or not settings.self_coding:
        raise HTTPException(status_code=403, detail="self-coding mutation is disabled")

    from pathlib import Path

    from keprix.mutation.self_coding_harness import SelfCodingRequest, run_scoped_mutation

    request = SelfCodingRequest(
        task=body.task,
        target_dir=body.target_dir,
        workspace_id=_workspace_id(),
        requested_by="operator",
        run_tests=body.run_tests,
    )
    result = await run_scoped_mutation(
        request,
        get_mutation_store(),
        Path(settings.repo_root).resolve(),
    )
    if result.mutation_id is None:
        raise HTTPException(status_code=422, detail=result.error or "scoped mutation failed")
    return {
        "mutation_id": result.mutation_id,
        "branch_name": result.branch_name,
        "test_passed": result.test_passed,
        "scope_valid": result.scope_valid,
    }


@router.get("/code")
async def list_code_mutations(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    items, total = get_mutation_store().list_mutations(
        _workspace_id(),
        tier="code",
        status=status,
        page=page,
        per_page=per_page,
    )
    return {
        "items": [_record_dict(item) for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/code/{record_id}")
async def get_code_mutation(
    record_id: str,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    record = get_mutation_store().get_generated_tool(record_id)
    if record is None or record.tier != "code":
        raise HTTPException(status_code=404, detail="code mutation not found")
    return _record_dict(record)


@router.get("/code/{record_id}/diff")
async def get_code_mutation_diff(
    record_id: str,
    _session: str = Depends(require_developer_session),
) -> dict[str, str]:
    record = get_mutation_store().get_generated_tool(record_id)
    if record is None or record.tier != "code":
        raise HTTPException(status_code=404, detail="code mutation not found")
    if not record.source_code:
        raise HTTPException(status_code=404, detail="no diff on record")
    return {"id": record.id, "diff": record.source_code}


@router.get("/code/{record_id}/test-output")
async def get_code_mutation_test_output(
    record_id: str,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    record = get_mutation_store().get_generated_tool(record_id)
    if record is None or record.tier != "code":
        raise HTTPException(status_code=404, detail="code mutation not found")
    return {
        "id": record.id,
        "test_output": record.metadata.get("test_output"),
        "test_passed": record.metadata.get("test_passed"),
    }


@router.post("/code/{record_id}/approve")
async def approve_code_mutation(
    record_id: str,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    record = get_mutation_store().approve_mutation(record_id, approved_by="api")
    if record is None:
        raise HTTPException(status_code=404, detail="code mutation not found or merge failed")
    return _record_dict(record)


@router.post("/code/{record_id}/reject")
async def reject_code_mutation(
    record_id: str,
    body: RejectBody,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    record = get_mutation_store().reject_mutation(record_id, rejected_by="api", reason=body.reason)
    if record is None:
        raise HTTPException(status_code=404, detail="code mutation not found")
    return _record_dict(record)


@router.post("/code/{record_id}/rollback")
async def rollback_code_mutation(
    record_id: str,
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    record = get_mutation_store().rollback_mutation(record_id, rolled_back_by="api")
    if record is None:
        raise HTTPException(status_code=404, detail="code mutation not found")
    return _record_dict(record)


@router.get("/quality/{mutation_id}")
async def get_mutation_quality_history(
    mutation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    store = get_mutation_store()
    record = store.get_generated_tool(mutation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="mutation not found")
    from keprix.mutation.quality import get_quality_scorer

    samples = get_quality_scorer().get_quality_history(mutation_id, limit=limit)
    return {
        "mutation_id": mutation_id,
        "quality_score": record.quality_score,
        "use_count": record.use_count,
        "samples": [
            {
                "outcome": sample.outcome,
                "score": sample.score,
                "run_id": sample.run_id,
                "task_id": sample.task_id,
                "feedback": sample.feedback,
                "sampled_at": sample.sampled_at.isoformat(),
            }
            for sample in samples
        ],
    }


@router.get("/compounding")
async def get_compounding_metrics(
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    from keprix.mutation.compounding import compute_compounding_metrics

    return compute_compounding_metrics(_workspace_id()).to_dict()


@router.post("/prune")
async def prune_mutations(
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    from keprix.mutation.pruner import get_mutation_pruner

    report = get_mutation_pruner().run_full_prune(workspace_id=_workspace_id())
    return {
        "pruned_tools": report.pruned_tools,
        "pruned_prompts": report.pruned_prompts,
        "pruned_code": report.pruned_code,
        "total_pruned": report.total_pruned,
        "space_reclaimed_bytes": report.space_reclaimed_bytes,
    }


@router.post("/prune/dry-run")
async def prune_mutations_dry_run(
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    from keprix.mutation.pruner import get_mutation_pruner

    report = get_mutation_pruner().run_full_prune(dry_run=True, workspace_id=_workspace_id())
    return {
        "pruned_tools": report.pruned_tools,
        "pruned_prompts": report.pruned_prompts,
        "pruned_code": report.pruned_code,
        "total_pruned": report.total_pruned,
        "space_reclaimed_bytes": report.space_reclaimed_bytes,
        "dry_run": True,
    }


"""Agent tools: sheet_preprocess_propose / sheet_preprocess_apply (Soft Wall)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.registry import registry

from keprix.crm.soft_wall import gate_or_approve
from keprix.sheet_preprocess import service as sheet_service

TOOLSET = "crm"


def check_sheet_preprocess_requirements() -> bool:
    return True


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _require_workspace(args: dict[str, Any]) -> str | None:
    ws = str(args.get("workspace_id") or "").strip()
    return ws or None


def _actor(args: dict[str, Any]) -> tuple[str, str]:
    return "agent", str(args.get("actor_id") or args.get("user_id") or "agent")


def sheet_preprocess_propose(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    actor_type, actor_id = _actor(args)
    upload_id = args.get("upload_id")
    source_path = args.get("source_path") or args.get("path")
    # Allow agent to point at a local file: copy into upload dir first.
    if not upload_id and source_path and Path(str(source_path)).is_file():
        try:
            meta = sheet_service.seed_upload_from_path(workspace_id, source_path)
            upload_id = meta["upload_id"]
            source_path = None
        except Exception as exc:
            return _err(str(exc), error_code="upload_failed")

    user_schema = args.get("user_schema")
    if isinstance(user_schema, str):
        try:
            user_schema = json.loads(user_schema)
        except json.JSONDecodeError:
            return _err("user_schema must be an object or JSON object string")

    try:
        job = sheet_service.propose_sheet(
            workspace_id,
            upload_id=str(upload_id) if upload_id else None,
            source_path=str(source_path) if source_path else None,
            user_schema=user_schema if isinstance(user_schema, dict) else None,
            metrics=args.get("metrics"),
            context=str(args.get("context") or ""),
            domain_pack=str(args.get("domain_pack") or "generic"),
            build_crm_plan=bool(args.get("build_crm_plan", True)),
            actor_type=actor_type,
            actor_id=actor_id,
        )
    except FileNotFoundError as exc:
        return _err(str(exc), error_code="not_found")
    except PermissionError:
        return _err("path_outside_workspace", error_code="path_outside_workspace")
    except ValueError as exc:
        return _err(str(exc), error_code="propose_failed")

    job_id = job.get("id")
    return _ok(
        {
            "enrichment_job": job,
            "workspace_id": workspace_id,
            "deep_link": f"/crm/enrich?job={job_id}",
            "metrics": job.get("metrics"),
        }
    )


def sheet_preprocess_apply(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    job_id = str(args.get("job_id") or args.get("id") or "").strip()
    if not job_id:
        return _err("job_id is required")
    actor_type, actor_id = _actor(args)
    force = bool(args.get("force"))
    approval_id = args.get("approval_id")
    upsert_crm = bool(args.get("upsert_crm", True))

    existing = sheet_service.get_job(workspace_id, job_id)
    if not existing:
        return _err("not_found", error_code="enrichment_not_found")

    gate = gate_or_approve(
        workspace_id,
        kind="apply_enrichment",
        subject=f"Apply sheet preprocess job {job_id}",
        payload={
            "job_id": job_id,
            "sheet_type": existing.get("sheet_type"),
            "upsert_crm": upsert_crm,
        },
        object_type="enrichment_job",
        object_id=job_id,
        actor_id=actor_id,
        force=force,
        approval_id=str(approval_id) if approval_id else None,
    )
    if gate.get("blocked"):
        approval = gate.get("approval") or {}
        return _ok(
            {
                "blocked": True,
                "error_code": gate.get("error_code") or "soft_wall_required",
                "approval": approval,
                "deep_link": f"/crm/enrich?job={job_id}",
                "workspace_id": workspace_id,
            }
        )

    try:
        updated = sheet_service.apply_sheet_job(
            workspace_id,
            job_id,
            upsert_crm=upsert_crm,
            actor_type=actor_type,
            actor_id=actor_id,
        )
    except LookupError:
        return _err("not_found", error_code="enrichment_not_found")
    except (FileNotFoundError, ValueError, PermissionError) as exc:
        return _err(str(exc), error_code="apply_failed")

    crm = (updated.get("apply_result") or {}).get("crm") or {}
    list_id = crm.get("list_id")
    return _ok(
        {
            "blocked": False,
            "enrichment_job": updated,
            "workspace_id": workspace_id,
            "deep_link": f"/crm/enrich?job={job_id}",
            "list_id": list_id,
            "list_deep_link": f"/crm/lists/{list_id}" if list_id else None,
            "leads_deep_link": "/crm/leads",
            "metrics": updated.get("metrics"),
        }
    )


def _ws_props(**extra: Any) -> dict[str, Any]:
    props = {"workspace_id": {"type": "string"}}
    props.update(extra)
    return props


registry.register(
    name="sheet_preprocess_propose",
    toolset=TOOLSET,
    schema={
        "name": "sheet_preprocess_propose",
        "description": (
            "Propose column roles and blank-cell fills for a spreadsheet. "
            "Does not write CRM or mutate the file. Returns /crm/enrich?job= deep link."
        ),
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                upload_id={"type": "string"},
                source_path={"type": "string"},
                path={"type": "string"},
                user_schema={"type": "object"},
                metrics={"type": "array", "items": {"type": "string"}},
                context={"type": "string"},
                domain_pack={"type": "string"},
                build_crm_plan={"type": "boolean"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=sheet_preprocess_propose,
    check_fn=check_sheet_preprocess_requirements,
)

registry.register(
    name="sheet_preprocess_apply",
    toolset=TOOLSET,
    schema={
        "name": "sheet_preprocess_apply",
        "description": (
            "Apply a sheet preprocess job after Soft Wall approval (or force). "
            "Fills blank cells only; optionally upserts CRM leads and returns deep links."
        ),
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                job_id={"type": "string"},
                id={"type": "string"},
                approval_id={"type": "string"},
                force={"type": "boolean"},
                upsert_crm={"type": "boolean"},
            ),
            "required": ["workspace_id", "job_id"],
        },
    },
    handler=sheet_preprocess_apply,
    check_fn=check_sheet_preprocess_requirements,
)

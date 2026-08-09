"""HTTP routes for Keprix CRM (/api/crm/*) with Soft Wall gates."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from keprix.auth.dependencies import get_current_user
from keprix.crm.deliverability import compute_deliverability_snapshot
from keprix.crm.identity import IdentityResolver
from keprix.crm.roles import require_cap
from keprix.crm.soft_wall import (
    PAYING_STAGES,
    gate_or_approve,
    pending_crm_approvals,
    resolve_crm_approval,
)
from keprix.crm.store import ConflictError, get_crm_store
from keprix.crm.models import OutboxStatus

router = APIRouter(prefix="/api/crm", tags=["crm"])


def _uid(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _workspace(
    workspace_id: str | None,
    x_workspace_id: str | None,
    user: dict[str, Any],
) -> str:
    return (workspace_id or x_workspace_id or _uid(user) or "default").strip() or "default"


def _store():
    return get_crm_store()


def _corr(request: Request) -> str:
    return request.headers.get("X-Correlation-Id") or str(uuid.uuid4())


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    q: str | None = None,
    stage: str | None = None,
    source: str | None = None,
    domain_pack: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    out = rows
    if stage:
        out = [r for r in out if str(r.get("stage") or "") == stage]
    if source:
        out = [r for r in out if str(r.get("source") or "") == source]
    if domain_pack:
        out = [r for r in out if str(r.get("domain_pack") or "") == domain_pack]
    if tag:
        out = [r for r in out if tag in (r.get("tags") or [])]
    if q:
        needle = q.lower()
        filtered: list[dict[str, Any]] = []
        for r in out:
            blob = " ".join(
                str(r.get(k) or "")
                for k in ("name", "display_name", "company_name", "company_number", "domain")
            ).lower()
            emails = r.get("emails") or []
            email_blob = " ".join(
                str(e.get("address") if isinstance(e, dict) else e) for e in emails
            ).lower()
            if needle in blob or needle in email_blob:
                filtered.append(r)
        out = filtered
    return out


def _page(rows: list[dict[str, Any]], *, limit: int, offset: int) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    return {
        "items": rows[offset : offset + limit],
        "count": len(rows),
        "limit": limit,
        "offset": offset,
    }


def _http_conflict(exc: ConflictError) -> HTTPException:
    return HTTPException(status_code=409, detail={"error_code": "version_conflict", "message": str(exc)})


class LeadCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    company_name: str | None = None
    company_number: str | None = None
    email: str | None = None
    emails: list[Any] | None = None
    phones: list[Any] | None = None
    source: str | None = None
    domain_pack: str | None = None
    stage: str | None = None
    tags: list[str] | None = None
    scores: dict[str, Any] | None = None
    account_id: str | None = None
    external_source_id: str | None = None
    assigned_agent: str | None = None
    website: str | None = None
    niche: str | None = None
    locality: str | None = None
    priority: str | None = None
    notes: str | None = None
    pipeline_stage: str | None = None


class LeadPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    company_name: str | None = None
    company_number: str | None = None
    email: str | None = None
    emails: list[Any] | None = None
    phones: list[Any] | None = None
    source: str | None = None
    domain_pack: str | None = None
    stage: str | None = None
    tags: list[str] | None = None
    scores: dict[str, Any] | None = None
    account_id: str | None = None
    assigned_agent: str | None = None
    expected_version: int | None = None
    approval_id: str | None = None
    website: str | None = None
    niche: str | None = None
    locality: str | None = None
    google_maps_url: str | None = None
    google_reviews: str | None = None
    google_rating: str | None = None
    website_score: str | None = None
    ranks_top3: str | None = None
    weakness: str | None = None
    priority: str | None = None
    notes: str | None = None
    source_type: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_captured_at: str | None = None
    owner_agent_id: str | None = None
    owner_user_id: str | None = None
    list_id: str | None = None
    campaign_id: str | None = None
    sequence_id: str | None = None
    pipeline_stage: str | None = None
    last_contacted_at: str | None = None
    last_reply_at: str | None = None
    next_action_at: str | None = None
    consent_status: str | None = None
    suppression_reason: str | None = None
    custom_fields: dict[str, Any] | None = None
    archived_at: str | None = None
    last_touch_at: str | None = None


class ListCreate(BaseModel):
    name: str
    description: str | None = None
    domain_pack: str | None = None
    source: str | None = None
    tags: list[str] | None = None


class ListMemberCreate(BaseModel):
    member_type: str = Field(pattern="^(lead|contact)$")
    member_id: str
    stage: str | None = None


class BulkSoftDelete(BaseModel):
    ids: list[str]
    preview: bool = True
    reason: str | None = None


class BulkLeadPatch(BaseModel):
    ids: list[str]
    patch: dict[str, Any] = Field(default_factory=dict)
    expected_versions: dict[str, int] | None = None
    approval_id: str | None = None
    force: bool = False
    tags_add: list[str] | None = None
    add_to_list_id: str | None = None


class BulkLeadArchive(BaseModel):
    ids: list[str]
    preview: bool = False
    expected_versions: dict[str, int] | None = None


class LeadExportWorkbook(BaseModel):
    ids: list[str] | None = None
    filter: dict[str, Any] | None = None
    format: str = "xlsx"


class SavedViewCreate(BaseModel):
    name: str
    visibility: str = "private"
    config: dict[str, Any] = Field(default_factory=dict)


class SavedViewPatch(BaseModel):
    name: str | None = None
    visibility: str | None = None
    config: dict[str, Any] | None = None


class EnrichApplyBody(BaseModel):
    approval_id: str | None = None
    force: bool = False


class EnrollApproveBody(BaseModel):
    sequence_id: str | None = None
    campaign_id: str | None = None
    approval_id: str | None = None
    force: bool = False


class EnrollExecuteBody(BaseModel):
    sequence_id: str | None = None
    campaign_id: str | None = None
    audience_hash: str | None = None
    content_hash: str | None = None
    require_soft_wall: bool = True
    force: bool = False
    approval_id: str | None = None
    start_immediately: bool = True


class MergeApplyBody(BaseModel):
    survivor_id: str | None = None
    approval_id: str | None = None
    force: bool = False


class KillSwitchBody(BaseModel):
    scope: str = "workspace"
    scope_id: str | None = None
    enabled: bool = True
    reason: str | None = None
    approval_id: str | None = None
    force: bool = False


class DemoSeedPurgeBody(BaseModel):
    approval_id: str | None = None
    force: bool = False


class OutboxActionBody(BaseModel):
    approval_id: str | None = None
    force: bool = False


class SuppressionBulkBody(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    preview: bool = True
    approval_id: str | None = None
    force: bool = False


class MergeRejectBody(BaseModel):
    reason: str | None = None


# ── Health / overview ─────────────────────────────────────────
@router.get("/status")
async def crm_status(
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = _store()
    return {
        "ok": True,
        "workspace_id": ws,
        "correlation_id": _corr(request),
        "counts": {
            "accounts": len(store.list_accounts(ws, limit=5000)),
            "leads": len(store.list_leads(ws, limit=5000)),
            "contacts": len(store.list_contacts(ws, limit=5000)),
            "deals": len(store.list_deals(ws, limit=5000)),
            "lists": len(store.list_lists(ws, limit=5000)),
            "pending_approvals": len(pending_crm_approvals(ws)),
        },
    }


# ── Leads ─────────────────────────────────────────────────────
@router.get("/leads")
async def list_leads(
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    q: str | None = None,
    stage: str | None = None,
    source: str | None = None,
    domain_pack: str | None = None,
    tag: str | None = None,
    priority: str | None = None,
    consent_status: str | None = None,
    suppressed: bool | None = None,
    sort: str = "updated_at",
    order: str = "desc",
    limit: int = 100,
    offset: int | None = None,
    cursor: str | None = None,
    include_archived: bool = False,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    # Prefer SQL filter/sort/keyset; fall back keeps offset clients working.
    page = _store().query_leads(
        ws,
        q=q,
        stage=stage,
        source=source,
        tag=tag,
        priority=priority,
        consent_status=consent_status,
        suppressed=suppressed,
        domain_pack=domain_pack,
        include_archived=include_archived,
        sort=sort,
        order=order,
        limit=limit,
        cursor=cursor,
        offset=offset if cursor is None else None,
    )
    # Backward-compatible count alias.
    page["count"] = page.get("total", len(page.get("items") or []))
    page["workspace_id"] = ws
    page["correlation_id"] = _corr(request)
    return page


@router.post("/leads", status_code=201)
async def create_lead(
    body: LeadCreate,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = _store()
    if idempotency_key:
        remembered = store.get_idempotency(ws, scope="create_lead", idempotency_key=idempotency_key)
        if remembered:
            return {"lead": remembered.get("result"), "idempotent": True, "correlation_id": _corr(request)}
    fields = body.model_dump(exclude_none=True)
    fields["actor_type"] = "user"
    fields["actor_id"] = _uid(user)
    lead = store.upsert_lead(ws, **fields)
    if idempotency_key:
        store.remember_idempotency(ws, scope="create_lead", idempotency_key=idempotency_key, result=lead)
    return {"lead": lead, "correlation_id": _corr(request)}


@router.post("/leads/bulk-patch")
async def bulk_patch_leads(
    body: BulkLeadPatch,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = _store()
    patch = dict(body.patch or {})
    target_stage = patch.get("stage") or patch.get("pipeline_stage")
    soft_wall_payload: dict[str, Any] | None = None

    needs_stage_wall = target_stage in PAYING_STAGES
    needs_campaign_wall = bool(patch.get("campaign_id"))
    if needs_stage_wall or needs_campaign_wall:
        require_cap(user, "approve")
        kind = "stage_customer_paying" if needs_stage_wall else "mass_update"
        gate = gate_or_approve(
            ws,
            kind=kind,
            subject=f"Bulk patch {len(body.ids)} leads"
            + (f" to {target_stage}" if needs_stage_wall else " campaign proposal"),
            payload={
                "ids": body.ids,
                "patch": patch,
                "kind": kind,
            },
            object_type="lead_bulk",
            object_id=",".join(body.ids[:8]),
            actor_id=_uid(user),
            approval_id=body.approval_id,
            force=body.force,
        )
        if gate.get("blocked"):
            return {
                "updated": [],
                "failed": [],
                "soft_wall": gate,
                "blocked": True,
                "error_code": gate.get("error_code"),
                "approval": gate.get("approval"),
                "correlation_id": _corr(request),
            }
        soft_wall_payload = gate

    updated: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    versions = body.expected_versions or {}
    for lead_id in dict.fromkeys(body.ids):
        existing = store.get_lead(ws, lead_id)
        if not existing:
            failed.append({"id": lead_id, "error_code": "lead_not_found"})
            continue
        lead_patch = dict(patch)
        if body.tags_add:
            merged = list(dict.fromkeys([*(existing.get("tags") or []), *body.tags_add]))
            lead_patch["tags"] = merged
        if body.add_to_list_id:
            lead_patch["list_id"] = body.add_to_list_id
        expected = versions.get(lead_id)
        try:
            row = store.update_lead(
                ws,
                lead_id,
                expected_version=expected,
                actor_type="user",
                actor_id=_uid(user),
                **lead_patch,
            )
            if row and body.add_to_list_id:
                try:
                    store.add_list_member(
                        ws,
                        body.add_to_list_id,
                        member_type="lead",
                        member_id=lead_id,
                    )
                except Exception:
                    pass
            if row:
                updated.append(row)
            else:
                failed.append({"id": lead_id, "error_code": "update_failed"})
        except ConflictError as exc:
            failed.append({"id": lead_id, "error_code": "version_conflict", "message": str(exc)})
        except Exception as exc:
            failed.append({"id": lead_id, "error_code": "update_error", "message": str(exc)})

    return {
        "updated": updated,
        "failed": failed,
        "soft_wall": soft_wall_payload,
        "correlation_id": _corr(request),
    }


@router.post("/leads/bulk-archive")
async def bulk_archive_leads(
    body: BulkLeadArchive,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from datetime import datetime, timezone

    ids = list(dict.fromkeys(body.ids))
    if body.preview:
        return {
            "preview": True,
            "count": len(ids),
            "ids": ids,
            "correlation_id": _corr(request),
        }
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return await bulk_patch_leads(
        BulkLeadPatch(
            ids=ids,
            patch={"archived_at": now},
            expected_versions=body.expected_versions,
        ),
        request,
        workspace_id=ws,
        x_workspace_id=None,
        user=user,
    )


@router.post("/leads/export-workbook")
async def export_leads_workbook(
    body: LeadExportWorkbook,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
):
    require_cap(user, "export")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = _store()
    filt = dict(body.filter or {})
    if body.ids:
        page = store.query_leads(ws, ids=list(body.ids), include_archived=True, limit=max(len(body.ids), 1))
        leads = page["items"]
    else:
        page = store.query_leads(
            ws,
            q=filt.get("q"),
            stage=filt.get("stage"),
            source=filt.get("source"),
            tag=filt.get("tag"),
            priority=filt.get("priority"),
            consent_status=filt.get("consent_status"),
            suppressed=filt.get("suppressed"),
            include_archived=bool(filt.get("include_archived")),
            sort=str(filt.get("sort") or "updated_at"),
            order=str(filt.get("order") or "desc"),
            limit=min(int(filt.get("limit") or 5000), 5000),
        )
        leads = page["items"]

    from keprix.crm.ingestion.export import export_leads

    fmt = (body.format or "xlsx").lower().lstrip(".")
    suffix = ".csv" if fmt == "csv" else ".xlsx"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="keprix-leads-")
    tmp_path = Path(tmp.name)
    tmp.close()
    export_leads(leads, tmp_path, format=fmt)
    media = "text/csv" if fmt == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        path=str(tmp_path),
        media_type=media,
        filename=f"keprix-leads{suffix}",
    )


@router.post("/leads/ingest-preview")
async def leads_ingest_preview(
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.ingestion.readers import read_bytes, read_rows_list
    from keprix.crm.ingestion.service import preview_rows

    content_type = (request.headers.get("content-type") or "").lower()
    rows: list[dict[str, Any]] = []
    sample_limit = 20
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=422, detail={"error_code": "rows_or_file_required"})
        payload = await upload.read()  # type: ignore[union-attr]
        filename = getattr(upload, "filename", None) or "upload.csv"
        loaded = read_bytes(payload, filename=str(filename))
        rows = loaded.get("rows") or []
    else:
        body = await request.json()
        sample_limit = int(body.get("limit") or 20)
        if isinstance(body.get("rows"), list):
            loaded = read_rows_list(body["rows"])
            rows = loaded.get("rows") or []
        else:
            raise HTTPException(status_code=422, detail={"error_code": "rows_or_file_required"})
    preview = preview_rows(rows, limit=sample_limit)
    preview["workspace_id"] = ws
    preview["correlation_id"] = _corr(request)
    preview["enrich_deep_link"] = "/crm/enrich"
    return preview


@router.post("/leads/ingest")
async def leads_ingest(
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.ingestion.service import IngestOptions, ingest_bytes, ingest_row_array

    content_type = (request.headers.get("content-type") or "").lower()
    options_kwargs: dict[str, Any] = {
        "actor_id": _uid(user),
        "source_type": "spreadsheet",
    }
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=422, detail={"error_code": "rows_or_file_required"})
        payload = await upload.read()  # type: ignore[union-attr]
        filename = getattr(upload, "filename", None) or "upload.csv"
        options_kwargs["overwrite"] = str(form.get("overwrite") or "").lower() in {"1", "true", "yes"}
        options_kwargs["dry_run"] = str(form.get("dry_run") or "").lower() in {"1", "true", "yes"}
        options_kwargs["source_name"] = str(form.get("source_name") or filename)
        options = IngestOptions(**options_kwargs)
        result = ingest_bytes(
            ws,
            payload,
            filename=str(filename),
            store=_store(),
            options=options,
        )
    else:
        body = await request.json()
        options = IngestOptions(
            overwrite=bool(body.get("overwrite")),
            source_type=str(body.get("source_type") or "spreadsheet"),
            source_name=body.get("source_name"),
            source_url=body.get("source_url"),
            actor_id=_uid(user),
            dry_run=bool(body.get("dry_run")),
        )
        if isinstance(body.get("rows"), list):
            result = ingest_row_array(ws, body["rows"], store=_store(), options=options)
        else:
            raise HTTPException(status_code=422, detail={"error_code": "rows_or_file_required"})
    result["workspace_id"] = ws
    result["correlation_id"] = _corr(request)
    return result


@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    lead = _store().get_lead(ws, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail={"error_code": "lead_not_found"})
    return {"lead": lead}


@router.patch("/leads/{lead_id}")
async def patch_lead(
    lead_id: str,
    body: LeadPatch,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = _store()
    existing = store.get_lead(ws, lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail={"error_code": "lead_not_found"})
    data = body.model_dump(exclude_none=True)
    expected = data.pop("expected_version", None)
    approval_id = data.pop("approval_id", None)
    new_stage = data.get("stage") or data.get("pipeline_stage")
    if new_stage in PAYING_STAGES and new_stage != existing.get("stage"):
        require_cap(user, "approve")
        gate = gate_or_approve(
            ws,
            kind="stage_customer_paying",
            subject=f"Promote lead {lead_id} to {new_stage}",
            payload={"lead_id": lead_id, "from": existing.get("stage"), "to": new_stage},
            object_type="lead",
            object_id=lead_id,
            actor_id=_uid(user),
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {
                "blocked": True,
                "error_code": gate.get("error_code"),
                "approval": gate.get("approval"),
                "correlation_id": _corr(request),
            }
    try:
        updated = store.update_lead(ws, lead_id, expected_version=expected, **data)
    except ConflictError as exc:
        raise _http_conflict(exc) from exc
    return {"lead": updated, "correlation_id": _corr(request)}


@router.get("/leads/{lead_id}/provenance")
async def lead_provenance(
    lead_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    lead = _store().get_lead(ws, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail={"error_code": "lead_not_found"})
    items = _store().list_provenance(ws, entity_type="lead", entity_id=lead_id)
    return {"items": items, "count": len(items), "lead_id": lead_id}


@router.get("/leads/{lead_id}/activities")
async def lead_activities(
    lead_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    lead = _store().get_lead(ws, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail={"error_code": "lead_not_found"})
    items = _store().list_activities(ws, entity_type="lead", entity_id=lead_id)
    return {"items": items, "count": len(items), "lead_id": lead_id}


@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = _store().delete_lead(ws, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "lead_not_found"})
    return {"ok": True, "lead": row}


@router.post("/leads/bulk-delete")
async def bulk_delete_leads(
    body: BulkSoftDelete,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    ids = list(dict.fromkeys(body.ids))
    if body.preview:
        return {
            "preview": True,
            "count": len(ids),
            "ids": ids,
            "reason": body.reason,
            "correlation_id": _corr(request),
        }
    deleted = []
    for lid in ids:
        row = _store().delete_lead(ws, lid)
        if row:
            deleted.append(row["id"])
    return {"preview": False, "count": len(deleted), "deleted": deleted, "correlation_id": _corr(request)}


# ── Saved views ───────────────────────────────────────────────
@router.get("/views")
async def list_saved_views(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_saved_views(ws, owner_user_id=_uid(user))
    return {"items": items, "count": len(items), "workspace_id": ws}


@router.post("/views", status_code=201)
async def create_saved_view(
    body: SavedViewCreate,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    view = _store().create_saved_view(
        ws,
        name=body.name,
        owner_user_id=_uid(user),
        visibility=body.visibility,
        config=body.config,
    )
    return {"view": view}


@router.patch("/views/{view_id}")
async def patch_saved_view(
    view_id: str,
    body: SavedViewPatch,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        view = _store().update_saved_view(
            ws,
            view_id,
            actor_user_id=_uid(user),
            name=body.name,
            visibility=body.visibility,
            config=body.config,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"error_code": str(exc)}) from exc
    if not view:
        raise HTTPException(status_code=404, detail={"error_code": "view_not_found"})
    return {"view": view}


@router.delete("/views/{view_id}")
async def delete_saved_view(
    view_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        ok = _store().delete_saved_view(ws, view_id, actor_user_id=_uid(user))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"error_code": str(exc)}) from exc
    if not ok:
        raise HTTPException(status_code=404, detail={"error_code": "view_not_found"})
    return {"ok": True}

# ── Accounts / contacts / deals (CRUD) ────────────────────────
def _crud_list(entity: str, list_fn, create_fn, get_fn, patch_fn, delete_fn):
    @router.get(f"/{entity}")
    async def _list(
        request: Request,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        q: str | None = None,
        stage: str | None = None,
        source: str | None = None,
        domain_pack: str | None = None,
        tag: str | None = None,
        limit: int = 100,
        offset: int = 0,
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "view")
        ws = _workspace(workspace_id, x_workspace_id, user)
        rows = _filter_rows(
            list_fn(_store(), ws),
            q=q,
            stage=stage,
            source=source,
            domain_pack=domain_pack,
            tag=tag,
        )
        page = _page(rows, limit=limit, offset=offset)
        page["workspace_id"] = ws
        page["correlation_id"] = _corr(request)
        return page

    @router.post(f"/{entity}", status_code=201)
    async def _create(
        request: Request,
        body: dict[str, Any] = Body(default_factory=dict),
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "edit")
        ws = _workspace(workspace_id, x_workspace_id, user)
        payload = dict(body or {})
        payload["actor_type"] = "user"
        payload["actor_id"] = _uid(user)
        row = create_fn(_store(), ws, payload)
        key = entity[:-1] if entity.endswith("s") else entity
        return {key: row, "correlation_id": _corr(request)}

    @router.get(f"/{entity}/{{row_id}}")
    async def _get(
        row_id: str,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "view")
        ws = _workspace(workspace_id, x_workspace_id, user)
        row = get_fn(_store(), ws, row_id)
        if not row:
            raise HTTPException(status_code=404, detail={"error_code": f"{entity}_not_found"})
        key = entity[:-1] if entity.endswith("s") else entity
        return {key: row}

    @router.patch(f"/{entity}/{{row_id}}")
    async def _patch(
        row_id: str,
        body: dict[str, Any],
        request: Request,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "edit")
        ws = _workspace(workspace_id, x_workspace_id, user)
        data = dict(body)
        expected = data.pop("expected_version", None)
        approval_id = data.pop("approval_id", None)
        existing = get_fn(_store(), ws, row_id)
        if not existing:
            raise HTTPException(status_code=404, detail={"error_code": f"{entity}_not_found"})
        new_stage = data.get("stage")
        if new_stage in PAYING_STAGES and new_stage != existing.get("stage"):
            require_cap(user, "approve")
            gate = gate_or_approve(
                ws,
                kind="stage_customer_paying",
                subject=f"Promote {entity} {row_id} to {new_stage}",
                payload={"id": row_id, "from": existing.get("stage"), "to": new_stage},
                object_type=entity[:-1] if entity.endswith("s") else entity,
                object_id=row_id,
                actor_id=_uid(user),
                approval_id=approval_id,
            )
            if gate.get("blocked"):
                return {
                    "blocked": True,
                    "error_code": gate.get("error_code"),
                    "approval": gate.get("approval"),
                    "correlation_id": _corr(request),
                }
        try:
            updated = patch_fn(_store(), ws, row_id, data, expected)
        except ConflictError as exc:
            raise _http_conflict(exc) from exc
        key = entity[:-1] if entity.endswith("s") else entity
        return {key: updated, "correlation_id": _corr(request)}

    @router.delete(f"/{entity}/{{row_id}}")
    async def _delete(
        row_id: str,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "edit")
        ws = _workspace(workspace_id, x_workspace_id, user)
        row = delete_fn(_store(), ws, row_id)
        if not row:
            raise HTTPException(status_code=404, detail={"error_code": f"{entity}_not_found"})
        return {"ok": True, entity[:-1] if entity.endswith("s") else entity: row}

    return _list, _create, _get, _patch, _delete


_crud_list(
    "accounts",
    list_fn=lambda s, ws: s.list_accounts(ws, limit=5000),
    create_fn=lambda s, ws, body: s.create_account(
        ws,
        str(body.pop("name", None) or "Untitled"),
        **{k: v for k, v in body.items() if k != "name"},
    ),
    get_fn=lambda s, ws, rid: s.get_account(ws, rid),
    patch_fn=lambda s, ws, rid, data, expected: s.update_account(ws, rid, expected_version=expected, **data),
    delete_fn=lambda s, ws, rid: s.delete_account(ws, rid),
)
_crud_list(
    "contacts",
    list_fn=lambda s, ws: s.list_contacts(ws, limit=5000),
    create_fn=lambda s, ws, body: s.create_contact(
        ws,
        str(body.pop("display_name", None) or body.pop("name", None) or "Untitled"),
        **body,
    ),
    get_fn=lambda s, ws, rid: s.get_contact(ws, rid),
    patch_fn=lambda s, ws, rid, data, expected: s.update_contact(ws, rid, expected_version=expected, **data),
    delete_fn=lambda s, ws, rid: s.delete_contact(ws, rid),
)
_crud_list(
    "deals",
    list_fn=lambda s, ws: s.list_deals(ws, limit=5000),
    create_fn=lambda s, ws, body: s.create_deal(
        ws,
        str(body.pop("name", None) or "Untitled deal"),
        **body,
    ),
    get_fn=lambda s, ws, rid: s.get_deal(ws, rid),
    patch_fn=lambda s, ws, rid, data, expected: s.update_deal(ws, rid, expected_version=expected, **data),
    delete_fn=lambda s, ws, rid: s.delete_deal(ws, rid),
)


# ── Lists + membership ────────────────────────────────────────
@router.get("/lists")
async def list_lists(
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    page = _page(_store().list_lists(ws, limit=5000), limit=limit, offset=offset)
    page["workspace_id"] = ws
    page["correlation_id"] = _corr(request)
    return page


@router.post("/lists", status_code=201)
async def create_list(
    body: ListCreate,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = _store().create_list(ws, body.name, **body.model_dump(exclude_none=True, exclude={"name"}))
    return {"list": row, "correlation_id": _corr(request)}


@router.get("/lists/{list_id}")
async def get_list(
    list_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = _store().get_list(ws, list_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "list_not_found"})
    members = _store().list_memberships(ws, list_id)
    return {"list": row, "members": members}


@router.patch("/lists/{list_id}")
async def patch_list(
    list_id: str,
    body: dict[str, Any],
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    data = dict(body or {})
    expected = data.pop("expected_version", None)
    data.pop("approval_id", None)
    if not _store().get_list(ws, list_id):
        raise HTTPException(status_code=404, detail={"error_code": "list_not_found"})
    try:
        updated = _store().update_list(ws, list_id, expected_version=expected, **data)
    except ConflictError as exc:
        raise _http_conflict(exc) from exc
    return {"list": updated, "correlation_id": _corr(request)}


@router.delete("/lists/{list_id}")
async def delete_list(
    list_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = _store().delete_list(ws, list_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "list_not_found"})
    return {"ok": True, "list": row}


@router.post("/lists/{list_id}/members", status_code=201)
async def add_list_member(
    list_id: str,
    body: ListMemberCreate,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        member = _store().add_list_member(
            ws,
            list_id,
            member_type=body.member_type,
            member_id=body.member_id,
            stage=body.stage,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "list_not_found"}) from None
    return {"membership": member, "correlation_id": _corr(request)}


@router.post("/lists/{list_id}/approve-enroll")
async def approve_list_enroll(
    list_id: str,
    body: EnrollApproveBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Soft Wall gate before enroll; prefer /enroll-preflight + /enroll (442)."""
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    lst = _store().get_list(ws, list_id)
    if not lst:
        raise HTTPException(status_code=404, detail={"error_code": "list_not_found"})
    members = _store().list_memberships(ws, list_id)
    from keprix.discovery.materialize import enroll_requires_soft_wall

    high_risk = enroll_requires_soft_wall(lst.get("domain_pack"))
    gate = gate_or_approve(
        ws,
        kind="approve_list_enroll_high_risk" if high_risk else "approve_list_enroll",
        subject=f"Approve list '{lst.get('name')}' for Soft Wall enroll ({len(members)} members)",
        payload={
            "list_id": list_id,
            "member_count": len(members),
            "sequence_id": body.sequence_id,
            "campaign_id": body.campaign_id,
            "domain_pack": lst.get("domain_pack"),
            "high_risk": high_risk,
        },
        object_type="list",
        object_id=list_id,
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
        always_require=high_risk,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code"),
            "approval": gate.get("approval"),
            "correlation_id": _corr(request),
        }
    updated = _store().update_list(ws, list_id, status="approved_for_enroll", stage="approved")
    return {
        "blocked": False,
        "list": updated,
        "member_count": len(members),
        "enroll_ready": True,
        "correlation_id": _corr(request),
    }


@router.post("/lists/{list_id}/enroll-preflight")
async def list_enroll_preflight(
    list_id: str,
    body: EnrollApproveBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.enroll import preflight_crm_list_enroll

    sequence_id = str(body.sequence_id or "").strip()
    if not sequence_id:
        raise HTTPException(status_code=422, detail={"error_code": "sequence_id_required"})
    try:
        report = preflight_crm_list_enroll(
            workspace_id=ws,
            list_id=list_id,
            sequence_id=sequence_id,
            campaign_id=body.campaign_id,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "list_not_found"}) from None
    report["correlation_id"] = _corr(request)
    return report


@router.post("/lists/{list_id}/enroll")
async def list_enroll(
    list_id: str,
    body: EnrollExecuteBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.enroll import enroll_list

    sequence_id = str(body.sequence_id or "").strip()
    if not sequence_id:
        raise HTTPException(status_code=422, detail={"error_code": "sequence_id_required"})
    result = enroll_list(
        workspace_id=ws,
        list_id=list_id,
        sequence_id=sequence_id,
        campaign_id=body.campaign_id,
        audience_hash=body.audience_hash,
        content_hash=body.content_hash,
        require_soft_wall=body.require_soft_wall,
        force=body.force,
        approval_id=body.approval_id,
        start_immediately=body.start_immediately,
        actor_id=_uid(user),
    )
    result["correlation_id"] = _corr(request)
    return result


# ── Activities ────────────────────────────────────────────────
@router.get("/activities")
async def list_activities(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    entity_type: str | None = None,
    entity_id: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_activities(ws, entity_type=entity_type, entity_id=entity_id)
    return {"items": items, "count": len(items)}


@router.post("/activities", status_code=201)
async def create_activity(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    if not body.get("entity_type") or not body.get("entity_id") or not body.get("activity_type"):
        raise HTTPException(status_code=400, detail={"error_code": "activity_fields_required"})
    row = _store().create_activity(
        ws,
        entity_type=str(body["entity_type"]),
        entity_id=str(body["entity_id"]),
        activity_type=str(body["activity_type"]),
        channel=body.get("channel"),
        subject=body.get("subject"),
        body=body.get("body"),
        metadata=body.get("metadata"),
        actor_type="user",
        actor_id=_uid(user),
    )
    return {"activity": row}


# ── Enrichments ───────────────────────────────────────────────
@router.get("/enrichments")
async def list_enrichments(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_enrichment_jobs(ws)
    return {"items": items, "count": len(items)}


@router.post("/enrichments", status_code=201)
async def create_enrichment(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    job = _store().create_enrichment_job(ws, actor_type="user", actor_id=_uid(user), **body)
    return {"enrichment_job": job}


@router.post("/enrichments/{job_id}/apply")
async def apply_enrichment(
    job_id: str,
    body: EnrichApplyBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    job = _store().get_enrichment_job(ws, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error_code": "enrichment_not_found"})
    gate = gate_or_approve(
        ws,
        kind="apply_enrichment",
        subject=f"Apply enrichment job {job_id}",
        payload={"job_id": job_id, "sheet_type": job.get("sheet_type")},
        object_type="enrichment_job",
        object_id=job_id,
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code"),
            "approval": gate.get("approval"),
            "correlation_id": _corr(request),
            "deep_link": f"/crm/enrich?job={job_id}",
        }
    # Prefer full sheet apply when a source path exists.
    if job.get("source_path"):
        try:
            from keprix.sheet_preprocess import service as sheet_service

            updated = sheet_service.apply_sheet_job(
                ws,
                job_id,
                upsert_crm=True,
                actor_type="user",
                actor_id=_uid(user),
            )
            return {
                "blocked": False,
                "enrichment_job": updated,
                "correlation_id": _corr(request),
                "deep_link": f"/crm/enrich?job={job_id}",
            }
        except Exception:
            pass
    updated = _store().update_enrichment_job(ws, job_id, status="applied")
    return {
        "blocked": False,
        "enrichment_job": updated,
        "correlation_id": _corr(request),
        "deep_link": f"/crm/enrich?job={job_id}",
    }


# ── Suppressions / consent ────────────────────────────────────
@router.get("/suppressions")
async def list_suppressions(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_suppressions(ws)
    return {"items": items, "count": len(items)}


@router.post("/suppressions", status_code=201)
async def create_suppression(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = _store().create_suppression_entry(ws, actor_type="user", actor_id=_uid(user), **body)
    return {"suppression": row}


@router.delete("/suppressions/{entry_id}")
async def delete_suppression(
    entry_id: str,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    approval_id: str | None = Query(default=None),
    force: bool = Query(default=False),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Undo suppression (Soft Wall gated)."""
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    gate = gate_or_approve(
        ws,
        kind="suppress_undo",
        subject=f"Undo suppression {entry_id}",
        payload={"entry_id": entry_id},
        object_type="suppression",
        object_id=entry_id,
        actor_id=_uid(user),
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code"),
            "approval": gate.get("approval"),
            "correlation_id": _corr(request),
        }
    row = _store().delete_suppression_entry(ws, entry_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "suppression_not_found"})
    return {"blocked": False, "suppression": row, "correlation_id": _corr(request)}


@router.post("/suppressions/bulk")
async def bulk_suppressions(
    body: SuppressionBulkBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    rows = body.rows or []
    if body.preview:
        return {
            "preview": True,
            "count": len(rows),
            "sample": rows[:20],
            "correlation_id": _corr(request),
        }
    gate = gate_or_approve(
        ws,
        kind="suppress_bulk_import",
        subject=f"Bulk suppress {len(rows)} addresses",
        payload={"count": len(rows)},
        object_type="suppression_bulk",
        object_id=ws,
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code"),
            "approval": gate.get("approval"),
            "correlation_id": _corr(request),
        }
    created: list[dict[str, Any]] = []
    for row in rows:
        created.append(
            _store().create_suppression_entry(
                ws,
                actor_type="user",
                actor_id=_uid(user),
                address=row.get("address"),
                channel=row.get("channel") or "email",
                reason=row.get("reason") or "bulk_import",
                source=row.get("source") or "operator_bulk",
            )
        )
    return {"blocked": False, "preview": False, "count": len(created), "items": created}


# ── Jobs / outbox / merges / contactability / deliverability ──
@router.get("/jobs")
async def list_jobs(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    discovery = _store().list_discovery_jobs(ws)
    enrich = _store().list_enrichment_jobs(ws)
    return {
        "discovery_jobs": discovery,
        "enrichment_jobs": enrich,
        "count": len(discovery) + len(enrich),
    }


@router.get("/outbox")
async def list_outbox(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    status: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_outbox(ws, status=status)
    dead = sum(1 for i in items if str(i.get("status") or "").lower() == "dead_letter")
    return {"items": items, "count": len(items), "dead_letter_count": dead}


@router.post("/outbox/{outbox_id}/retry")
async def retry_outbox(
    outbox_id: str,
    body: OutboxActionBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Re-queue dead_letter/failed using the same idempotency key (no double-send invent)."""
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_outbox(ws, limit=5000)
    row = next((i for i in items if i.get("id") == outbox_id), None)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "outbox_not_found"})
    status = str(row.get("status") or "").lower()
    if status not in {"dead_letter", "failed"}:
        raise HTTPException(status_code=400, detail={"error_code": "outbox_not_retryable", "status": status})
    gate = gate_or_approve(
        ws,
        kind="outbox_retry",
        subject=f"Retry outbox {outbox_id}",
        payload={"outbox_id": outbox_id, "idempotency_key": row.get("idempotency_key")},
        object_type="outbox",
        object_id=outbox_id,
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code"),
            "approval": gate.get("approval"),
            "correlation_id": _corr(request),
        }
    updated = _store().update_outbox(
        ws,
        outbox_id,
        status=OutboxStatus.PENDING,
        last_error=None,
        attempts=int(row.get("attempts") or 0),
    )
    return {
        "blocked": False,
        "outbox": updated,
        "idempotency_key": row.get("idempotency_key"),
        "correlation_id": _corr(request),
    }


@router.post("/outbox/{outbox_id}/cancel")
async def cancel_outbox(
    outbox_id: str,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_outbox(ws, limit=5000)
    row = next((i for i in items if i.get("id") == outbox_id), None)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "outbox_not_found"})
    status = str(row.get("status") or "").lower()
    if status not in {"pending", "failed"}:
        raise HTTPException(status_code=400, detail={"error_code": "outbox_not_cancellable", "status": status})
    updated = _store().update_outbox(ws, outbox_id, status="cancelled", last_error="cancelled_by_operator")
    return {"outbox": updated, "correlation_id": _corr(request)}


@router.get("/merges")
async def list_merges(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_merge_suggestions(ws)
    return {"items": items, "count": len(items)}


@router.post("/merges/{suggestion_id}/apply")
async def apply_merge(
    suggestion_id: str,
    body: MergeApplyBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    suggestion = _store().get_merge_suggestion(ws, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail={"error_code": "merge_not_found"})
    gate = gate_or_approve(
        ws,
        kind="merge_identity",
        subject=f"Merge {suggestion.get('entity_type')} {suggestion.get('left_id')} / {suggestion.get('right_id')}",
        payload={"suggestion_id": suggestion_id},
        object_type="merge_suggestion",
        object_id=suggestion_id,
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code"),
            "approval": gate.get("approval"),
            "correlation_id": _corr(request),
        }
    resolver = IdentityResolver(_store())
    result = resolver.apply_merge_suggestion(
        ws,
        suggestion_id,
        survivor_id=body.survivor_id,
        actor_type="user",
        actor_id=_uid(user),
    )
    return {"blocked": False, **result, "correlation_id": _corr(request)}


@router.post("/merges/{suggestion_id}/reject")
async def reject_merge(
    suggestion_id: str,
    body: MergeRejectBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    suggestion = _store().get_merge_suggestion(ws, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail={"error_code": "merge_not_found"})
    updated = _store().update_merge_suggestion(
        ws,
        suggestion_id,
        status="rejected",
        explanation=body.reason or suggestion.get("explanation"),
    )
    return {"ok": True, "suggestion": updated, "correlation_id": _corr(request)}


@router.get("/contactability")
async def list_contactability(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_contactability(ws)
    return {"items": items, "count": len(items)}


@router.put("/contactability")
async def upsert_contactability(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = _store().upsert_contactability(ws, actor_type="user", actor_id=_uid(user), **body)
    return {"decision": row}


@router.get("/deliverability")
async def list_deliverability(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    return compute_deliverability_snapshot(_store(), ws)


@router.put("/deliverability/sender-readiness")
async def upsert_sender_readiness(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    domain = str(body.get("domain") or "")
    if not domain:
        raise HTTPException(status_code=400, detail={"error_code": "domain_required"})
    row = _store().upsert_sender_readiness(ws, domain, actor_type="user", actor_id=_uid(user), **body)
    return {"sender_readiness": row}


@router.get("/kill-switches")
async def list_kill_switches(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    return {"items": _store().list_kill_switches(ws)}


@router.put("/kill-switches")
async def upsert_kill_switch(
    body: KillSwitchBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    # Turning kill switch off (enabled=False means not blocking) requires Soft Wall.
    turning_off = body.enabled is False
    if turning_off:
        gate = gate_or_approve(
            ws,
            kind="kill_switch_off",
            subject=f"Disable kill switch scope={body.scope}",
            payload=body.model_dump(),
            object_type="kill_switch",
            object_id=body.scope_id or body.scope,
            actor_id=_uid(user),
            force=body.force,
            approval_id=body.approval_id,
        )
        if gate.get("blocked"):
            return {
                "blocked": True,
                "error_code": gate.get("error_code"),
                "approval": gate.get("approval"),
                "correlation_id": _corr(request),
            }
    row = _store().upsert_kill_switch(
        ws,
        scope=body.scope,
        scope_id=body.scope_id,
        enabled=body.enabled,
        reason=body.reason,
        actor_type="user",
        actor_id=_uid(user),
    )
    return {"blocked": False, "kill_switch": row, "correlation_id": _corr(request)}


# ── Soft Wall approvals ───────────────────────────────────────
@router.get("/approvals")
async def list_approvals(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    kind: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = pending_crm_approvals(ws, kind=kind)
    return {"items": items, "count": len(items)}


@router.post("/approvals/{approval_id}/approve")
async def approve_item(
    approval_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = resolve_crm_approval(ws, approval_id, status="approved")
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "approval_not_found"})
    return {"ok": True, "approval": row}


@router.post("/approvals/{approval_id}/reject")
async def reject_item(
    approval_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = resolve_crm_approval(ws, approval_id, status="rejected")
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "approval_not_found"})
    return {"ok": True, "approval": row}


# ── Inbox / engagement (443) ──────────────────────────────────
@router.get("/inbox")
async def get_inbox(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    status: str | None = Query(default="open"),
    kind: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.engagement import list_inbox

    items = list_inbox(_store(), ws, status=status, kind=kind)
    return {"items": items, "count": len(items)}


@router.post("/inbox/{item_id}/claim")
async def claim_inbox_item(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.engagement import update_inbox_item

    row = update_inbox_item(_store(), ws, item_id, status="claimed", assignee=_uid(user))
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "inbox_not_found"})
    return {"item": row}


@router.post("/inbox/{item_id}/pause")
async def pause_inbox_item(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.engagement import update_inbox_item

    row = update_inbox_item(_store(), ws, item_id, status="paused")
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "inbox_not_found"})
    return {"item": row}


@router.post("/inbox/{item_id}/resume")
async def resume_inbox_item(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.engagement import update_inbox_item

    row = update_inbox_item(_store(), ws, item_id, status="open")
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "inbox_not_found"})
    return {"item": row}


@router.post("/engagement/ingest")
async def engagement_ingest(
    body: dict[str, Any] = Body(default_factory=dict),
    request: Request = None,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    from keprix.crm.engagement import ingest_engagement

    result = ingest_engagement(
        workspace_id=ws,
        engagement_type=str(body.get("engagement_type") or body.get("classification") or "replied"),
        body=str(body.get("body") or ""),
        subject=str(body.get("subject") or ""),
        from_address=body.get("from_address"),
        outreach_lead_id=body.get("outreach_lead_id"),
        confidence=float(body.get("confidence") or 1.0),
        method=str(body.get("method") or "api"),
        provider=str(body.get("provider") or "api"),
        provider_event_id=body.get("provider_event_id"),
        channel=str(body.get("channel") or "email"),
        actor_id=_uid(user),
    )
    return result


# ── Workflows / nurture (444) ─────────────────────────────────
@router.get("/workflows")
async def list_crm_workflows(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.nurture import ensure_default_nurture_sequence, list_workflows

    ensure_default_nurture_sequence(ws)
    items = list_workflows(ws)
    return {"items": items, "count": len(items)}


@router.post("/workflows/{sequence_id}/status")
async def set_crm_workflow_status(
    sequence_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.nurture import set_workflow_status

    status = str(body.get("status") or "").strip()
    try:
        row = set_workflow_status(ws, sequence_id, status, actor_id=_uid(user))
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "workflow_not_found"}) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error_code": "invalid_status", "message": str(exc)}) from None
    return row


@router.post("/workflows")
async def create_crm_workflow(
    body: dict[str, Any] = Body(default_factory=dict),
    request: Request = None,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    from keprix.crm.nurture import create_or_adjust_nurture

    result = create_or_adjust_nurture(
        ws,
        name=str(body.get("name") or "CRM nurture"),
        steps=body.get("steps"),
        meta=body.get("meta"),
        sequence_id=body.get("sequence_id"),
        require_soft_wall=bool(body.get("require_soft_wall", True)),
        force=bool(body.get("force")),
        approval_id=body.get("approval_id"),
        actor_id=_uid(user),
    )
    return result


# ── Funnel analytics (447) ────────────────────────────────────
@router.get("/funnel")
async def crm_funnel(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    campaign_id: str | None = None,
    pack: str | None = None,
    days: int = 30,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.funnel_analytics import funnel_snapshot

    return funnel_snapshot(ws, campaign_id=campaign_id, pack=pack, days=days, crm_store=_store())


@router.get("/digest")
async def crm_digest(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    hours: int = 24,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.funnel_analytics import build_digest

    return build_digest(ws, hours=hours, crm_store=_store())


# ── Booking offer (445) ───────────────────────────────────────
@router.post("/contacts/{contact_id}/offer-booking")
async def offer_booking_contact(
    contact_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.booking import offer_booking

    return offer_booking(
        ws,
        contact_id=contact_id,
        host_user_id=body.get("host_user_id") or _uid(user),
        event_type_id=body.get("event_type_id") or body.get("vical_event_type_id"),
        campaign_id=body.get("campaign_id"),
        crm_store=_store(),
    )


@router.post("/leads/{lead_id}/offer-booking")
async def offer_booking_lead(
    lead_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.booking import offer_booking

    return offer_booking(
        ws,
        lead_id=lead_id,
        host_user_id=body.get("host_user_id") or _uid(user),
        event_type_id=body.get("event_type_id") or body.get("vical_event_type_id"),
        campaign_id=body.get("campaign_id"),
        crm_store=_store(),
    )


# ── Consent / compliance (448) ────────────────────────────────
@router.get("/consents")
async def list_consents(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    subject_id: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    items = _store().list_consent_records(ws)
    if subject_id:
        items = [i for i in items if str(i.get("subject_id")) == subject_id]
    return {"items": items, "count": len(items)}


@router.post("/consents", status_code=201)
async def create_consent_route(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.compliance import create_consent

    try:
        row = create_consent(
            _store(),
            ws,
            subject_type=str(body.get("subject_type") or "contact"),
            subject_id=str(body.get("subject_id") or ""),
            channel=str(body.get("channel") or "email"),
            lawful_basis=str(body.get("lawful_basis") or body.get("basis") or ""),
            purpose=str(body.get("purpose") or "outreach"),
            evidence=body.get("evidence"),
            source=body.get("source"),
            actor_type="user",
            actor_id=_uid(user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error_code": "invalid_consent", "message": str(exc)}) from None
    return {"consent": row}


@router.get("/compliance/policy")
async def get_compliance_policy(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.compliance import get_workspace_policy

    return {"policy": get_workspace_policy(_store(), ws)}


@router.post("/leads/{lead_id}/export")
async def lead_subject_export(
    lead_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    gate = gate_or_approve(
        ws,
        kind="crm_subject_export",
        subject=f"Subject access export lead/{lead_id}",
        payload={"entity_type": "lead", "entity_id": lead_id},
        object_type="lead",
        object_id=lead_id,
        actor_id=_uid(user),
        force=bool(body.get("force")),
        approval_id=body.get("approval_id"),
    )
    if gate.get("blocked"):
        return {"blocked": True, "approval": gate.get("approval"), "error_code": gate.get("error_code")}
    from keprix.crm.compliance import subject_access_export

    return {"blocked": False, "export": subject_access_export(_store(), ws, subject_type="lead", subject_id=lead_id)}


@router.post("/contacts/{contact_id}/export")
async def contact_subject_export(
    contact_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    gate = gate_or_approve(
        ws,
        kind="crm_subject_export",
        subject=f"Subject access export contact/{contact_id}",
        payload={"entity_type": "contact", "entity_id": contact_id},
        object_type="contact",
        object_id=contact_id,
        actor_id=_uid(user),
        force=bool(body.get("force")),
        approval_id=body.get("approval_id"),
    )
    if gate.get("blocked"):
        return {"blocked": True, "approval": gate.get("approval"), "error_code": gate.get("error_code")}
    from keprix.crm.compliance import subject_access_export

    return {
        "blocked": False,
        "export": subject_access_export(_store(), ws, subject_type="contact", subject_id=contact_id),
    }


@router.get("/settings/summary")
async def crm_settings_summary(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.compliance import get_workspace_policy
    from keprix.crm.deliverability import compute_deliverability_snapshot

    return {
        "kill_switches": _store().list_kill_switches(ws),
        "policy": get_workspace_policy(_store(), ws),
        "deliverability": compute_deliverability_snapshot(_store(), ws),
        "cadence_defaults": {"max_emails_per_week": 3, "quiet_hours": [18, 8], "timezone": "Europe/London"},
    }


@router.get("/demo-seed/status")
async def crm_demo_seed_status(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.demo_seed import demo_seed_status

    return demo_seed_status(ws)


@router.post("/demo-seed/purge")
async def crm_demo_seed_purge(
    body: DemoSeedPurgeBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.demo_seed import demo_seed_status, purge_crm_demo

    status = demo_seed_status(ws)
    if not status.get("present"):
        return {
            "ok": True,
            "blocked": False,
            "present": False,
            "removed": {},
            "hint": "No demo-seed CRM rows to remove.",
            "correlation_id": _corr(request),
        }

    gate = gate_or_approve(
        ws,
        kind="crm_demo_purge",
        subject="Remove local CRM demo-seed data",
        payload={"counts": status.get("counts"), "confirm": "purge-demo-seed"},
        object_type="demo_seed",
        object_id="local",
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code"),
            "approval": gate.get("approval"),
            "present": True,
            "counts": status.get("counts"),
            "correlation_id": _corr(request),
        }

    result = purge_crm_demo(ws)
    return {
        "blocked": False,
        "ok": True,
        "correlation_id": _corr(request),
        **result,
    }


# ── Visual CRM surfaces (506-515) ─────────────────────────────
@router.get("/visual/contract")
async def crm_visual_contract(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.visual_contract import visual_contract_payload

    return visual_contract_payload()


@router.get("/visual/pipeline-board")
async def crm_pipeline_board(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    saved_view: str | None = None,
    q: str | None = None,
    owner: str | None = None,
    source: str | None = None,
    pack: str | None = None,
    stage: str | None = None,
    tag: str | None = None,
    contactability: str | None = None,
    limit_per_lane: int = 50,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.pipeline_board import build_pipeline_board

    filters = {
        "q": q,
        "owner": owner,
        "source": source,
        "pack": pack,
        "stage": stage,
        "tag": tag,
        "contactability": contactability,
    }
    return build_pipeline_board(
        ws,
        crm_store=_store(),
        filters=filters,
        saved_view=saved_view,
        limit_per_lane=max(1, min(limit_per_lane, 200)),
    )


@router.post("/visual/pipeline-board/preview-transition")
async def crm_pipeline_preview_transition(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    from keprix.crm.pipeline_board import preview_stage_transition

    return preview_stage_transition(
        ws,
        crm_store=_store(),
        entity_type=str(body.get("entity_type") or "lead"),
        entity_id=str(body.get("entity_id") or ""),
        to_stage=str(body.get("to_stage") or ""),
        human_confirmed=bool(body.get("human_confirmed")),
        soft_wall_approved=bool(body.get("soft_wall_approved")),
        expected_version=body.get("expected_version"),
    )


@router.post("/visual/pipeline-board/transition")
async def crm_pipeline_transition(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    from keprix.crm.pipeline_board import commit_stage_transition

    return commit_stage_transition(
        ws,
        crm_store=_store(),
        entity_type=str(body.get("entity_type") or "lead"),
        entity_id=str(body.get("entity_id") or ""),
        to_stage=str(body.get("to_stage") or ""),
        human_confirmed=bool(body.get("human_confirmed")),
        soft_wall_approved=bool(body.get("soft_wall_approved")),
        force=bool(body.get("force")),
        expected_version=body.get("expected_version"),
        actor_id=_uid(user),
        reason=body.get("reason"),
    )


@router.get("/visual/workflows/{workflow_id}")
async def crm_visual_workflow(
    workflow_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.workflow_graph import get_or_build_workflow_graph, list_templates, validate_graph
    from keprix.crm.visual_contract import NODE_FAMILY_GROUPS
    from keprix.crm.workflow_graph import NODE_PALETTE

    try:
        graph = get_or_build_workflow_graph(ws, workflow_id)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "workflow_not_found"}) from None
    return {
        "graph": graph,
        "validation": validate_graph(graph),
        "palette": NODE_PALETTE,
        "groups": {k: list(v) for k, v in NODE_FAMILY_GROUPS.items()},
        "templates": list_templates(),
    }


@router.put("/visual/workflows/{workflow_id}")
async def crm_visual_workflow_save(
    workflow_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.workflow_graph import save_workflow_graph, validate_graph

    graph = dict(body.get("graph") or body)
    graph["id"] = workflow_id
    result = save_workflow_graph(
        ws,
        graph,
        actor_id=_uid(user),
        expected_version=body.get("expected_version"),
    )
    if result.get("conflict"):
        raise HTTPException(status_code=409, detail=result)
    result["validation"] = validate_graph(result.get("graph") or graph)
    return result


@router.post("/visual/workflows/{workflow_id}/validate")
async def crm_visual_workflow_validate(
    workflow_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.workflow_graph import get_or_build_workflow_graph, validate_graph

    ws = _workspace(workspace_id, x_workspace_id, user)
    graph = body.get("graph")
    if not graph:
        try:
            graph = get_or_build_workflow_graph(ws, workflow_id)
        except LookupError:
            raise HTTPException(status_code=404, detail={"error_code": "workflow_not_found"}) from None
    return validate_graph(graph)


@router.post("/visual/workflows/{workflow_id}/simulate")
async def crm_visual_workflow_simulate(
    workflow_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.workflow_graph import get_or_build_workflow_graph, simulate_graph

    try:
        graph = body.get("graph") or get_or_build_workflow_graph(ws, workflow_id)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "workflow_not_found"}) from None
    return simulate_graph(graph, sample=body.get("sample"))


@router.post("/visual/workflows/{workflow_id}/publish")
async def crm_visual_workflow_publish(
    workflow_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.workflow_graph import publish_workflow_graph

    try:
        return publish_workflow_graph(ws, workflow_id, actor_id=_uid(user), reason=body.get("reason"))
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "workflow_not_found"}) from None


@router.get("/visual/templates")
async def crm_visual_templates(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.workflow_graph import list_templates, template_graph

    items = []
    for t in list_templates():
        items.append({**t, "preview": template_graph(t["id"])})
    return {"items": items, "count": len(items)}


@router.post("/visual/templates/{template_id}/instantiate")
async def crm_visual_template_instantiate(
    template_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.workflow_graph import save_workflow_graph, template_graph

    try:
        graph = template_graph(template_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error_code": "template_not_found"}) from None
    if body.get("name"):
        graph["name"] = str(body["name"])
    graph["status"] = "draft"
    graph["auto_active"] = False
    return save_workflow_graph(ws, graph, actor_id=_uid(user))


@router.get("/visual/runs")
async def crm_visual_runs(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    workflow_id: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.run_events import list_runs

    items = list_runs(ws, workflow_id=workflow_id)
    return {"items": items, "count": len(items)}


@router.post("/visual/runs")
async def crm_visual_create_run(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    from keprix.crm.run_events import create_run
    from keprix.crm.workflow_graph import get_or_build_workflow_graph

    workflow_id = str(body.get("workflow_id") or "")
    if not workflow_id:
        raise HTTPException(status_code=422, detail={"error_code": "workflow_id_required"})
    try:
        graph = get_or_build_workflow_graph(ws, workflow_id)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "workflow_not_found"}) from None
    run = create_run(
        ws,
        workflow_id=workflow_id,
        workflow_version=int(graph.get("workflow_version") or 1),
        subject_type=str(body.get("subject_type") or "lead"),
        subject_id=body.get("subject_id"),
        graph=graph,
    )
    return {"run": run}


@router.get("/visual/runs/compare")
async def crm_visual_run_compare(
    run_a: str,
    run_b: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.run_events import compare_runs

    try:
        return compare_runs(ws, run_a, run_b)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "run_not_found"}) from None


@router.get("/visual/runs/{run_id}")
async def crm_visual_run(
    run_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.run_events import run_snapshot

    try:
        return run_snapshot(ws, run_id)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "run_not_found"}) from None


@router.get("/visual/runs/{run_id}/events")
async def crm_visual_run_events(
    run_id: str,
    cursor: int = 0,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.run_events import run_events_since

    try:
        return run_events_since(ws, run_id, cursor=cursor)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "run_not_found"}) from None


@router.post("/visual/runs/{run_id}/step")
async def crm_visual_run_step(
    run_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.run_events import seed_demo_progression

    try:
        return seed_demo_progression(ws, run_id)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "run_not_found"}) from None


@router.get("/visual/inspector")
async def crm_visual_inspector(
    workflow_id: str,
    node_id: str,
    mode: str = "design",
    run_id: str | None = None,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.node_inspector import build_inspector
    from keprix.crm.run_events import get_run
    from keprix.crm.workflow_graph import get_or_build_workflow_graph

    try:
        graph = get_or_build_workflow_graph(ws, workflow_id)
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "workflow_not_found"}) from None
    run = get_run(ws, run_id) if run_id else None
    return build_inspector(mode=mode, graph=graph, node_id=node_id, run=run, workspace_id=ws)


@router.post("/visual/support-bundle")
async def crm_visual_support_bundle(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "export")
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    from keprix.crm.node_inspector import create_support_bundle
    from keprix.crm.run_events import get_run
    from keprix.crm.workflow_graph import get_or_build_workflow_graph

    graph = None
    run = None
    if body.get("workflow_id"):
        try:
            graph = get_or_build_workflow_graph(ws, str(body["workflow_id"]))
        except LookupError:
            pass
    if body.get("run_id"):
        run = get_run(ws, str(body["run_id"]))
    return create_support_bundle(
        ws,
        graph=graph,
        run=run,
        selected_node_ids=body.get("node_ids"),
    )


@router.get("/visual/metrics/definitions")
async def crm_metrics_definitions(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.metrics_semantic import definitions_payload

    return definitions_payload()


@router.post("/visual/metrics/query")
async def crm_metrics_query(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    from keprix.crm.metrics_semantic import query_metrics

    return query_metrics(
        ws,
        measures=body.get("measures"),
        dimensions=body.get("dimensions"),
        days=int(body.get("days") or 30),
        cohort=str(body.get("cohort") or "first_touch"),
        attribution=str(body.get("attribution") or "sourced"),
        crm_store=_store(),
    )


@router.post("/visual/metrics/backfill")
async def crm_metrics_backfill(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.metrics_semantic import backfill_from_crm

    return backfill_from_crm(ws, crm_store=_store())


@router.get("/visual/ops")
async def crm_visual_ops(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    from keprix.crm.ops_centre import build_ops_centre

    return build_ops_centre(ws, crm_store=_store())


@router.get("/visual/a11y-performance")
async def crm_visual_a11y_performance(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    return {
        "wcag": "2.2 AA",
        "reduced_motion": {"honor_prefers_reduced_motion": True, "user_override": True},
        "equivalents": {
            "canvas": "ordered_outline",
            "pipeline": "keyboard_move_dialog",
            "charts": "accessible_tables",
            "animation": "static_timeline",
        },
        "performance_budgets": {
            "initial_js_route_kb": 350,
            "interaction_ms": 100,
            "graph_layout_ms": 500,
            "event_latency_ms": 2000,
            "chart_query_ms": 1500,
        },
        "scale_targets": {
            "nodes_per_workflow": 80,
            "cards_per_lane": 200,
            "runs_per_campaign": 5000,
            "events_per_run": 500,
            "dashboard_range_days": 90,
            "concurrent_live_clients": 25,
        },
        "degradation": {
            "large_board": "paginate_lanes",
            "large_graph": "outline_and_server_layout",
            "high_volume_runs": "aggregate_mode",
        },
        "lazy_libraries": ["@xyflow/react", "apexcharts"],
    }

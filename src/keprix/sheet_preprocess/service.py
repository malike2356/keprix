"""Workspace-scoped sheet upload, propose, Soft Wall apply, and CRM upsert."""

from __future__ import annotations

import csv
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from keprix.sheet_preprocess.job_codec import (
    enrichment_job_from_store,
    estimate_cost,
    proposal_envelope,
)
from keprix.sheet_preprocess.processor import SheetPreprocessor, load_table_with_inspection
from keprix.sheet_preprocess.safety import SheetSafetyError, content_hash_file


def _home() -> Path:
    raw = os.environ.get("KEPRIX_SHEET_PREPROCESS_DIR")
    if raw:
        return Path(raw)
    for key in ("KEPRIX_DATA_DIR", "KEPRIX_HOME"):
        val = os.environ.get(key)
        if val:
            return Path(val) / "sheet_preprocess"
    try:
        from keprix_constants import get_keprix_home

        return Path(get_keprix_home()) / "sheet_preprocess"
    except Exception:
        return Path.home() / ".keprix" / "sheet_preprocess"


def workspace_root(workspace_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", (workspace_id or "default").strip()) or "default"
    root = _home() / safe
    root.mkdir(parents=True, exist_ok=True)
    (root / "uploads").mkdir(exist_ok=True)
    (root / "outputs").mkdir(exist_ok=True)
    return root


def _store():
    from keprix.crm.store import get_crm_store

    return get_crm_store()


def save_upload(
    workspace_id: str,
    *,
    filename: str,
    content: bytes,
    actor_type: str = "user",
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Persist an uploaded spreadsheet under the workspace upload dir."""
    if not content:
        raise ValueError("empty_upload")
    name = Path(filename or "upload.csv").name
    suffix = Path(name).suffix.lower()
    if suffix not in {".csv", ".tsv", ".xlsx"}:
        raise ValueError("unsupported_format")
    upload_id = str(uuid.uuid4())
    dest = workspace_root(workspace_id) / "uploads" / f"{upload_id}{suffix}"
    dest.write_bytes(content)
    meta = {
        "upload_id": upload_id,
        "filename": name,
        "path": str(dest),
        "size_bytes": len(content),
        "content_hash": content_hash_file(dest),
        "workspace_id": workspace_id,
        "actor_type": actor_type,
        "actor_id": actor_id,
    }
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, default=str), encoding="utf-8")
    return meta


def save_google_sheet_values(
    workspace_id: str,
    *,
    spreadsheet_id: str,
    values: list[list[Any]],
    title: str = "Google Sheet",
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Store Google Sheet values as the same canonical CSV used by file uploads."""
    if not spreadsheet_id.strip():
        raise ValueError("spreadsheet_id_required")
    if not values:
        raise ValueError("google_sheet_empty")
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerows(values)
    safe_title = Path(title or "Google Sheet").stem or "Google Sheet"
    meta = save_upload(
        workspace_id,
        filename=f"{safe_title}.csv",
        content=output.getvalue().encode("utf-8"),
        actor_type="google_sheet",
        actor_id=actor_id,
    )
    meta["source"] = {
        "kind": "google_sheet",
        "spreadsheet_id": spreadsheet_id,
    }
    meta_path = Path(meta["path"]).with_suffix(".csv.meta.json")
    meta_path.write_text(json.dumps(meta, default=str), encoding="utf-8")
    return meta


def resolve_source_path(workspace_id: str, *, upload_id: str | None = None, source_path: str | None = None) -> Path:
    root = workspace_root(workspace_id).resolve()
    if upload_id:
        matches = list((root / "uploads").glob(f"{upload_id}.*"))
        matches = [p for p in matches if not p.name.endswith(".meta.json")]
        if not matches:
            raise FileNotFoundError("upload_not_found")
        path = matches[0].resolve()
    elif source_path:
        path = Path(source_path).expanduser().resolve()
    else:
        raise ValueError("upload_id_or_source_path_required")
    # Fail closed: must live under workspace root unless KEPRIX_SHEET_ALLOW_ABS=1.
    allow_abs = os.environ.get("KEPRIX_SHEET_ALLOW_ABS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not allow_abs and root not in path.parents and path != root:
        # Also allow paths that were previously saved under this workspace.
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise PermissionError("path_outside_workspace") from exc
    if not path.is_file():
        raise FileNotFoundError("source_not_found")
    return path


def propose_sheet(
    workspace_id: str,
    *,
    upload_id: str | None = None,
    source_path: str | None = None,
    user_schema: dict[str, Any] | None = None,
    metrics: list[str] | None = None,
    context: str = "",
    domain_pack: str = "generic",
    sheet_name: str | int | None = None,
    header_row: int = 0,
    build_crm_plan: bool = True,
    actor_type: str = "user",
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Run propose and persist an enrichment job. Does not mutate the sheet."""
    path = resolve_source_path(workspace_id, upload_id=upload_id, source_path=source_path)
    preprocessor = SheetPreprocessor()
    try:
        frame, inspection = load_table_with_inspection(
            path,
            sheet_name=sheet_name,
            header_row=header_row,
            limits=preprocessor.limits,
        )
    except SheetSafetyError as exc:
        raise ValueError(str(exc)) from exc

    job = preprocessor.propose(
        frame,
        user_schema=user_schema,
        metrics=metrics,
        context=context,
        content_hash=inspection.content_hash,
        selected_worksheet=inspection.selected_worksheet if sheet_name is None else sheet_name,
        header_row=header_row,
        flattened_export=inspection.flattened_export,
        sheet_warnings=inspection.warnings,
        build_crm_plan=build_crm_plan,
        domain_pack=domain_pack,
    )
    cost = estimate_cost(job.proposal.blank_cells, len(job.proposal.fills))
    envelope = proposal_envelope(
        job,
        inspection=inspection.to_dict(),
        user_schema=user_schema or {},
    )
    store_row = _store().create_enrichment_job(
        workspace_id,
        status=job.status,
        sheet_type=job.proposal.sheet_type,
        source_path=str(path),
        domain_pack=domain_pack,
        proposal=envelope,
        cells_filled=0,
        cells_skipped=0,
        cost_estimate=cost,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return _job_public(store_row, deep_link=True)


def get_job(workspace_id: str, job_id: str) -> dict[str, Any] | None:
    row = _store().get_enrichment_job(workspace_id, job_id)
    if not row:
        return None
    return _job_public(row, deep_link=True)


def list_jobs(workspace_id: str) -> list[dict[str, Any]]:
    return [_job_public(r, deep_link=True) for r in _store().list_enrichment_jobs(workspace_id)]


def _job_public(row: dict[str, Any], *, deep_link: bool = False) -> dict[str, Any]:
    out = dict(row)
    proposal_blob = out.get("proposal") if isinstance(out.get("proposal"), dict) else {}
    proposal = proposal_blob.get("proposal") if isinstance(proposal_blob.get("proposal"), dict) else proposal_blob
    fills = proposal.get("fills") if isinstance(proposal, dict) else []
    blank = int(proposal.get("blank_cells") or 0) if isinstance(proposal, dict) else 0
    out["metrics"] = {
        "blank_cells": blank,
        "proposed_fills": len(fills) if isinstance(fills, list) else 0,
        "cells_filled": int(out.get("cells_filled") or 0),
        "cells_skipped": int(out.get("cells_skipped") or 0),
        "cost_estimate": out.get("cost_estimate"),
        "row_count": int(proposal.get("row_count") or 0) if isinstance(proposal, dict) else 0,
    }
    out["job_type"] = "sheet_preprocess"
    if deep_link:
        out["deep_link"] = f"/crm/enrich?job={out.get('id')}"
    apply_result = proposal_blob.get("apply_result") if isinstance(proposal_blob, dict) else None
    if apply_result:
        out["apply_result"] = apply_result
    return out


def _execute_crm_plan(
    workspace_id: str,
    plan_dict: dict[str, Any] | None,
    *,
    actor_type: str,
    actor_id: str | None,
    domain_pack: str,
    job_id: str,
) -> dict[str, Any]:
    """Apply CRM upsert plan rows (accounts/leads/contacts) and build a list."""
    store = _store()
    created: dict[str, list[str]] = {"accounts": [], "leads": [], "contacts": []}
    if not plan_dict or not plan_dict.get("rows"):
        return {"created": created, "list_id": None, "warnings": ["no_crm_plan_rows"]}

    account_by_row: dict[int, str] = {}
    lead_ids: list[str] = []

    for row in plan_dict["rows"]:
        if not isinstance(row, dict):
            continue
        et = str(row.get("entity_type") or "").lower()
        fields = dict(row.get("fields") or {})
        fields.setdefault("domain_pack", domain_pack)
        fields.setdefault("source", "sheet_preprocess")
        fields["actor_type"] = actor_type
        fields["actor_id"] = actor_id
        row_index = int(row.get("row_index") or 0)
        try:
            if et == "account":
                account = store.upsert_account(workspace_id, **fields)
                account_by_row[row_index] = account["id"]
                created["accounts"].append(account["id"])
            elif et == "lead":
                if row_index in account_by_row and not fields.get("account_id"):
                    fields["account_id"] = account_by_row[row_index]
                lead = store.upsert_lead(workspace_id, **fields)
                lead_ids.append(lead["id"])
                created["leads"].append(lead["id"])
            elif et == "contact":
                if row_index in account_by_row and not fields.get("account_id"):
                    fields["account_id"] = account_by_row[row_index]
                contact = store.upsert_contact(workspace_id, **fields)
                created["contacts"].append(contact["id"])
        except Exception as exc:
            # Fail soft per row; surface in apply_result.
            created.setdefault("errors", []).append({"row_index": row_index, "entity": et, "error": str(exc)})

    list_id = None
    if lead_ids:
        lst = store.create_list(
            workspace_id,
            name=f"Sheet enrich {job_id[:8]}",
            description=f"Leads from sheet preprocess job {job_id}",
            domain_pack=domain_pack,
            source="sheet_preprocess",
            tags=["sheet_preprocess"],
        )
        list_id = lst["id"]
        for lid in lead_ids:
            try:
                store.add_list_member(
                    workspace_id,
                    list_id,
                    member_type="lead",
                    member_id=lid,
                )
            except Exception:
                continue

    return {"created": created, "list_id": list_id, "lead_ids": lead_ids}


def apply_sheet_job(
    workspace_id: str,
    job_id: str,
    *,
    upsert_crm: bool = True,
    actor_type: str = "user",
    actor_id: str | None = None,
) -> dict[str, Any]:
    """
    Apply fills (empty cells only) and optionally execute CRM upsert plan.

    Caller must Soft Wall-gate before invoking this.
    """
    store = _store()
    row = store.get_enrichment_job(workspace_id, job_id)
    if not row:
        raise LookupError("enrichment_not_found")
    if str(row.get("status") or "") not in {"proposed", "partial"}:
        raise ValueError(f"job_not_applicable:{row.get('status')}")

    job = enrichment_job_from_store(row)
    source = row.get("source_path")
    if not source:
        raise ValueError("missing_source_path")
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError("source_not_found")

    preprocessor = SheetPreprocessor()
    frame, _inspection = load_table_with_inspection(path, limits=preprocessor.limits)
    out_name = f"{job_id}_enriched.csv"
    output_path = workspace_root(workspace_id) / "outputs" / out_name
    applied = preprocessor.apply(
        frame,
        job,
        output_path=output_path,
        build_crm_plan=False,
        domain_pack=str(row.get("domain_pack") or "generic"),
    )

    apply_result: dict[str, Any] = {
        "cells_filled": applied.cells_filled,
        "cells_skipped": applied.cells_skipped,
        "output_path": applied.output_path,
        "output_hash": applied.output_hash,
    }
    if upsert_crm:
        plan_blob = None
        proposal_blob = row.get("proposal") if isinstance(row.get("proposal"), dict) else {}
        if isinstance(proposal_blob, dict):
            plan_blob = proposal_blob.get("crm_upsert_plan")
        crm_result = _execute_crm_plan(
            workspace_id,
            plan_blob,
            actor_type=actor_type,
            actor_id=actor_id,
            domain_pack=str(row.get("domain_pack") or "generic"),
            job_id=job_id,
        )
        apply_result["crm"] = crm_result

    envelope = proposal_envelope(
        applied,
        inspection=(row.get("proposal") or {}).get("inspection")
        if isinstance(row.get("proposal"), dict)
        else {},
        user_schema=(row.get("proposal") or {}).get("user_schema")
        if isinstance(row.get("proposal"), dict)
        else {},
        apply_result=apply_result,
    )
    # Preserve crm plan on applied job.
    if isinstance(row.get("proposal"), dict) and row["proposal"].get("crm_upsert_plan"):
        envelope["crm_upsert_plan"] = row["proposal"]["crm_upsert_plan"]

    updated = store.update_enrichment_job(
        workspace_id,
        job_id,
        status="applied",
        output_path=str(output_path),
        cells_filled=applied.cells_filled,
        cells_skipped=applied.cells_skipped,
        proposal=envelope,
    )
    public = _job_public(updated or row, deep_link=True)
    public["apply_result"] = apply_result
    return public


def copy_output_for_download(workspace_id: str, job_id: str, *, output_format: str = "xlsx") -> Path:
    row = _store().get_enrichment_job(workspace_id, job_id)
    if not row:
        raise LookupError("enrichment_not_found")
    out = row.get("output_path")
    if not out or not Path(out).is_file():
        raise FileNotFoundError("output_not_found")
    path = Path(out).resolve()
    root = workspace_root(workspace_id).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PermissionError("path_outside_workspace") from exc
    fmt = output_format.strip().lower()
    if fmt == "csv":
        return path
    if fmt != "xlsx":
        raise ValueError("unsupported_export_format")

    destination = root / "outputs" / f"{job_id}_enriched.xlsx"
    if not destination.is_file() or destination.stat().st_mtime < path.stat().st_mtime:
        frame, _inspection = load_table_with_inspection(path)
        from keprix.sheet_preprocess.processor import write_table

        write_table(frame, destination)
    return destination


def publish_output_to_google_sheet(workspace_id: str, job_id: str) -> dict[str, Any]:
    """Publish a completed canonical CSV through the configured Google Workspace bridge."""
    path = copy_output_for_download(workspace_id, job_id, output_format="csv")
    frame, _inspection = load_table_with_inspection(path)
    values = [[str(column) for column in frame.columns]]
    import pandas as pd

    values.extend([["" if pd.isna(value) else value for value in row] for row in frame.itertuples(index=False, name=None)])
    from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge

    result = GoogleWorkspaceBridge().call(
        "gws_sheets_create",
        {"title": f"Keprix enriched sheet {job_id[:8]}", "values": values},
    )
    return {
        "spreadsheet_id": result.get("spreadsheet_id") or result.get("spreadsheetId"),
        "spreadsheet_url": result.get("spreadsheet_url") or result.get("spreadsheetUrl"),
        "result": result,
    }


def seed_upload_from_path(workspace_id: str, path: str | Path) -> dict[str, Any]:
    """Test/agent helper: copy an existing file into the upload dir."""
    src = Path(path)
    return save_upload(workspace_id, filename=src.name, content=src.read_bytes())

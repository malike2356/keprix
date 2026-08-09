"""Canonical CRM lead ingestion service (CSV/TSV/XLS/XLSX/ODS + row arrays)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.crm.ingestion.canonical import map_headers, normalize_row
from keprix.crm.ingestion.dedup import find_existing
from keprix.crm.ingestion.readers import read_bytes, read_path, read_rows_list
from keprix.crm.models import ProvenanceKind
from keprix.crm.store import CrmStore, get_crm_store
from keprix.sheet_preprocess.safety import SheetLimits, SheetSafetyError, looks_like_formula


@dataclass
class IngestOptions:
    overwrite: bool = False
    source_type: str = "spreadsheet"
    source_name: str | None = None
    source_url: str | None = None
    actor_id: str | None = None
    actor_type: str = "user"
    domain_pack: str = "generic"
    dry_run: bool = False
    reject_formula_fields: bool = False
    limits: SheetLimits = field(default_factory=SheetLimits)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _merge_nonempty(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    *,
    overwrite: bool,
) -> dict[str, Any]:
    """Merge incoming into a patch for update_lead."""
    skip = {"id", "workspace_id", "created_at", "updated_at", "version", "deleted_at"}
    patch: dict[str, Any] = {}
    for key, value in incoming.items():
        if key in skip or _is_empty(value):
            continue
        if key == "custom_fields" and isinstance(value, dict):
            base = existing.get("custom_fields") or {}
            if not isinstance(base, dict):
                base = {}
            merged = dict(base)
            for ck, cv in value.items():
                if overwrite or ck not in merged or _is_empty(merged.get(ck)):
                    if not _is_empty(cv):
                        merged[ck] = cv
            if merged != base:
                patch["custom_fields"] = merged
            continue
        if overwrite:
            patch[key] = value
            continue
        if _is_empty(existing.get(key)):
            patch[key] = value
    return patch


def _row_to_lead_fields(
    normalized: dict[str, Any],
    *,
    options: IngestOptions,
    source_job_id: str | None,
) -> dict[str, Any]:
    fields = dict(normalized)
    email = fields.pop("email", None)
    phone = fields.pop("phone", None)
    if email:
        fields["email"] = email
    if phone:
        fields["phone"] = phone
    fields.setdefault("source", options.source_type)
    fields.setdefault("source_type", options.source_type)
    if options.source_name:
        fields.setdefault("source_name", options.source_name)
    if options.source_url:
        fields.setdefault("source_url", options.source_url)
    if source_job_id:
        fields["source_job_id"] = source_job_id
    fields.setdefault("domain_pack", options.domain_pack)
    fields["actor_type"] = options.actor_type
    fields["actor_id"] = options.actor_id
    if fields.get("stage") and not fields.get("pipeline_stage"):
        fields["pipeline_stage"] = fields["stage"]
    return fields


def _reject_reason(fields: dict[str, Any]) -> str | None:
    if not any(
        [
            fields.get("email"),
            fields.get("phone"),
            fields.get("company_name"),
            fields.get("website"),
            fields.get("name"),
            fields.get("external_source_id"),
            fields.get("company_number"),
        ]
    ):
        return "empty_identity"
    return None


def preview_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int = 20,
) -> dict[str, Any]:
    headers = list(rows[0].keys()) if rows else []
    mapping = map_headers([str(h) for h in headers])
    unknown = [h for h in headers if h not in mapping]
    sample = []
    for raw in rows[:limit]:
        sample.append({"raw": raw, "normalized": normalize_row(raw, header_map=mapping)})
    return {
        "header_map": mapping,
        "unknown_headers": unknown,
        "row_count": len(rows),
        "sample": sample,
    }


def ingest_rows(
    workspace_id: str,
    rows: list[dict[str, Any]],
    *,
    store: CrmStore | None = None,
    options: IngestOptions | None = None,
    content_hash: str | None = None,
    source_format: str = "rows",
) -> dict[str, Any]:
    options = options or IngestOptions()
    store = store or get_crm_store()
    ws = store._require_workspace(workspace_id)

    job = store.create_ingestion_job(
        ws,
        source_type=options.source_type,
        source_name=options.source_name or source_format,
        content_hash=content_hash,
        status="running",
        actor_id=options.actor_id,
        metadata={"format": source_format, "dry_run": options.dry_run},
    )
    job_id = job["id"]

    headers = list(rows[0].keys()) if rows else []
    mapping = map_headers([str(h) for h in headers])
    warnings: list[str] = []
    created_ids: list[str] = []
    updated_ids: list[str] = []
    duplicate_ids: list[str] = []
    rejected: list[dict[str, Any]] = []
    created = updated = duplicate = rejected_count = 0

    source_record = None
    if not options.dry_run:
        source_record = store.create_source_record(
            ws,
            adapter=f"ingest:{options.source_type}",
            external_id=options.source_name,
            content_hash=content_hash,
            snapshot={
                "format": source_format,
                "row_count": len(rows),
                "header_map": mapping,
            },
        )

    for index, raw in enumerate(rows):
        try:
            # Formula policy: keep as text by default; optionally reject.
            formula_hits = [
                str(k)
                for k, v in raw.items()
                if isinstance(v, str) and looks_like_formula(v)
            ]
            if formula_hits and options.reject_formula_fields:
                rejected_count += 1
                rejected.append(
                    {
                        "row_index": index,
                        "reason": "unsafe_formula",
                        "fields": formula_hits,
                    }
                )
                continue
            if formula_hits:
                warnings.append(
                    f"row {index}: formula cell(s) kept as text: {', '.join(formula_hits)}"
                )

            normalized = normalize_row(raw, header_map=mapping)
            fields = _row_to_lead_fields(normalized, options=options, source_job_id=job_id)
            reason = _reject_reason(fields)
            if reason:
                rejected_count += 1
                rejected.append({"row_index": index, "reason": reason})
                continue

            existing = find_existing(store, ws, fields)
            if options.dry_run:
                if existing:
                    duplicate += 1
                    duplicate_ids.append(existing["id"])
                else:
                    created += 1
                continue

            if existing:
                patch = _merge_nonempty(existing, fields, overwrite=options.overwrite)
                if not patch:
                    duplicate += 1
                    duplicate_ids.append(existing["id"])
                    continue
                lead = store.update_lead(ws, existing["id"], **patch) or existing
                updated += 1
                updated_ids.append(lead["id"])
                action = "updated"
            else:
                lead = store.create_lead(ws, **fields)
                created += 1
                created_ids.append(lead["id"])
                action = "created"

            # Provenance for key fields.
            for field_name in (
                "company_name",
                "email",
                "phone",
                "website",
                "locality",
                "niche",
            ):
                value = fields.get(field_name) or (
                    (fields.get("emails") or [{}])[0]
                    if field_name == "email"
                    else None
                )
                if field_name == "email":
                    value = fields.get("email")
                if field_name == "phone":
                    value = fields.get("phone")
                if _is_empty(value):
                    continue
                store.record_provenance(
                    ws,
                    entity_type="lead",
                    entity_id=lead["id"],
                    field_name=field_name,
                    value=value,
                    kind=ProvenanceKind.OBSERVED,
                    source_url=options.source_url,
                    source_record_id=source_record["id"] if source_record else None,
                    adapter=f"ingest:{options.source_type}",
                    evidence_excerpt=f"{action} via ingestion job {job_id}",
                    confidence=1.0,
                    verification_state="imported",
                )
        except Exception as exc:
            rejected_count += 1
            rejected.append({"row_index": index, "reason": "error", "error": str(exc)})

    status = "completed"
    error_summary = None
    if rejected_count and not (created or updated or duplicate):
        status = "failed"
        error_summary = "all rows rejected"
    store.update_ingestion_job(
        ws,
        job_id,
        status=status,
        created_count=created,
        updated_count=updated,
        duplicate_count=duplicate,
        rejected_count=rejected_count,
        warning_count=len(warnings),
        error_summary=error_summary,
        metadata={
            "format": source_format,
            "header_map": mapping,
            "dry_run": options.dry_run,
        },
    )

    return {
        "job_id": job_id,
        "status": status,
        "created": created,
        "updated": updated,
        "duplicate": duplicate,
        "rejected": rejected_count,
        "warnings": warnings,
        "created_ids": created_ids,
        "updated_ids": updated_ids,
        "duplicate_ids": duplicate_ids,
        "rejected_rows": rejected,
        "header_map": mapping,
        "source_record_id": source_record["id"] if source_record else None,
    }


def ingest_file(
    workspace_id: str,
    path: str | Path,
    *,
    store: CrmStore | None = None,
    options: IngestOptions | None = None,
    sheet_name: str | int | None = None,
) -> dict[str, Any]:
    options = options or IngestOptions()
    try:
        loaded = read_path(path, sheet_name=sheet_name, limits=options.limits)
    except SheetSafetyError:
        raise
    warnings = list(loaded.get("warnings") or [])
    result = ingest_rows(
        workspace_id,
        loaded["rows"],
        store=store,
        options=options,
        content_hash=loaded.get("content_hash"),
        source_format=str(loaded.get("format") or Path(path).suffix.lstrip(".")),
    )
    result["warnings"] = warnings + list(result.get("warnings") or [])
    result["path"] = loaded.get("path") or str(path)
    return result


def ingest_bytes(
    workspace_id: str,
    payload: bytes,
    *,
    filename: str = "upload.csv",
    store: CrmStore | None = None,
    options: IngestOptions | None = None,
    sheet_name: str | int | None = None,
) -> dict[str, Any]:
    options = options or IngestOptions()
    loaded = read_bytes(
        payload,
        filename=filename,
        sheet_name=sheet_name,
        limits=options.limits,
    )
    warnings = list(loaded.get("warnings") or [])
    result = ingest_rows(
        workspace_id,
        loaded["rows"],
        store=store,
        options=options,
        content_hash=loaded.get("content_hash"),
        source_format=str(loaded.get("format") or "bytes"),
    )
    result["warnings"] = warnings + list(result.get("warnings") or [])
    return result


def ingest_row_array(
    workspace_id: str,
    rows: list[dict[str, Any]],
    *,
    store: CrmStore | None = None,
    options: IngestOptions | None = None,
) -> dict[str, Any]:
    options = options or IngestOptions()
    loaded = read_rows_list(rows, limits=options.limits)
    return ingest_rows(
        workspace_id,
        loaded["rows"],
        store=store,
        options=options,
        content_hash=loaded.get("content_hash"),
        source_format="rows",
    )


def ingest_channel_attachment(
    workspace_id: str,
    payload: bytes,
    *,
    filename: str,
    store: CrmStore | None = None,
    options: IngestOptions | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """Same ingestion path for authorised channel spreadsheet attachments.

    Channel adapters should call this instead of implementing separate parsers.
    Mailbox pollers may still be SIMULATED; once bytes are authorised, use this.
    """
    options = options or IngestOptions()
    if not options.source_type or options.source_type == "spreadsheet":
        options.source_type = "channel_attachment"
    if channel and not options.source_name:
        options.source_name = channel
    result = ingest_bytes(
        workspace_id,
        payload,
        filename=filename,
        store=store,
        options=options,
    )
    result["channel"] = channel
    return result

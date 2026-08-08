"""Serialize / deserialize EnrichmentJob payloads for CRM store JSON columns."""

from __future__ import annotations

from typing import Any

from keprix.sheet_preprocess.models import (
    ColumnRole,
    ColumnSpec,
    CrmUpsertPlan,
    CrmUpsertRow,
    EnrichmentJob,
    FillProposal,
    ReviewIssue,
    SheetProposal,
)
from keprix.sheet_preprocess.models import BatchCheckpoint


def column_spec_from_dict(name: str, raw: dict[str, Any]) -> ColumnSpec:
    role_raw = raw.get("role", "metric")
    role = ColumnRole(str(role_raw))
    allowed = raw.get("allowed_values") or ()
    if isinstance(allowed, str):
        allowed_values = (allowed,)
    else:
        allowed_values = tuple(str(item) for item in allowed)
    return ColumnSpec(
        name=str(raw.get("name") or name),
        role=role,
        metric=str(raw["metric"]) if raw.get("metric") is not None else None,
        data_type=str(raw.get("data_type") or "text"),
        description=str(raw.get("description") or ""),
        confidence=float(raw.get("confidence") or 1.0),
        source=str(raw.get("source") or "user"),
        units=str(raw["units"]) if raw.get("units") is not None else None,
        currency=str(raw["currency"]) if raw.get("currency") is not None else None,
        timezone=str(raw["timezone"]) if raw.get("timezone") is not None else None,
        allowed_values=allowed_values,
        validation=str(raw["validation"]) if raw.get("validation") is not None else None,
        required=bool(raw.get("required") or False),
        unique_key=bool(raw.get("unique_key") or False),
        metric_formula=str(raw["metric_formula"])
        if raw.get("metric_formula") is not None
        else None,
        pii_class=str(raw["pii_class"]) if raw.get("pii_class") is not None else None,
    )


def fill_from_dict(raw: dict[str, Any]) -> FillProposal:
    return FillProposal(
        row_index=int(raw["row_index"]),
        column=str(raw["column"]),
        value=raw.get("value"),
        confidence=float(raw["confidence"]) if raw.get("confidence") is not None else None,
        source=str(raw.get("source") or "model"),
        evidence=str(raw.get("evidence") or ""),
        provenance_kind=str(raw.get("provenance_kind") or "model_inferred"),
        adapter=str(raw.get("adapter") or "sheet_preprocess"),
        policy_version=str(raw.get("policy_version") or "sheet_preprocess.v1"),
        observed_at=str(raw["observed_at"]) if raw.get("observed_at") is not None else None,
        source_field=str(raw["source_field"]) if raw.get("source_field") is not None else None,
        verification_state=str(raw.get("verification_state") or "unverified"),
    )


def issue_from_dict(raw: dict[str, Any]) -> ReviewIssue:
    return ReviewIssue(
        code=str(raw.get("code") or "unknown"),
        message=str(raw.get("message") or ""),
        severity=str(raw.get("severity") or "warning"),
        row_index=int(raw["row_index"]) if raw.get("row_index") is not None else None,
        column=str(raw["column"]) if raw.get("column") is not None else None,
        detail=dict(raw.get("detail") or {}),
    )


def proposal_from_dict(raw: dict[str, Any]) -> SheetProposal:
    columns_raw = raw.get("columns") or {}
    columns: dict[str, ColumnSpec] = {}
    for name, spec in columns_raw.items():
        if isinstance(spec, dict):
            columns[str(name)] = column_spec_from_dict(str(name), spec)
    checkpoint_raw = raw.get("checkpoint") or {}
    checkpoint = BatchCheckpoint(
        next_row=int(checkpoint_raw.get("next_row") or 0),
        batches_completed=int(checkpoint_raw.get("batches_completed") or 0),
        tokens_used=int(checkpoint_raw.get("tokens_used") or 0),
        cancelled=bool(checkpoint_raw.get("cancelled") or False),
    )
    return SheetProposal(
        sheet_type=str(raw.get("sheet_type") or "generic"),
        columns=columns,
        fills=[fill_from_dict(item) for item in (raw.get("fills") or []) if isinstance(item, dict)],
        missing_metrics=[str(m) for m in (raw.get("missing_metrics") or [])],
        warnings=[str(w) for w in (raw.get("warnings") or [])],
        issues=[issue_from_dict(item) for item in (raw.get("issues") or []) if isinstance(item, dict)],
        row_count=int(raw.get("row_count") or 0),
        blank_cells=int(raw.get("blank_cells") or 0),
        analysed_rows=int(raw.get("analysed_rows") or 0),
        mode=str(raw.get("mode") or "auto_analyse"),
        mapping_version=str(raw.get("mapping_version") or "sheet_preprocess.v1"),
        content_hash=str(raw["content_hash"]) if raw.get("content_hash") is not None else None,
        selected_worksheet=raw.get("selected_worksheet"),
        header_row=int(raw.get("header_row") or 0),
        flattened_export=bool(raw.get("flattened_export") or False),
        checkpoint=checkpoint,
    )


def crm_plan_from_dict(raw: dict[str, Any] | None) -> CrmUpsertPlan | None:
    if not raw or not isinstance(raw, dict):
        return None
    rows: list[CrmUpsertRow] = []
    for item in raw.get("rows") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            CrmUpsertRow(
                entity_type=str(item.get("entity_type") or "Lead"),
                action=str(item.get("action") or "upsert"),
                fields=dict(item.get("fields") or {}),
                row_index=int(item.get("row_index") or 0),
                identity_keys=dict(item.get("identity_keys") or {}),
                provenance=dict(item.get("provenance") or {}),
            )
        )
    return CrmUpsertPlan(
        sheet_type=str(raw.get("sheet_type") or "generic"),
        rows=rows,
        warnings=[str(w) for w in (raw.get("warnings") or [])],
        mapping_version=str(raw.get("mapping_version") or "sheet_preprocess.v1"),
        source_content_hash=str(raw["source_content_hash"])
        if raw.get("source_content_hash") is not None
        else None,
    )


def enrichment_job_from_store(row: dict[str, Any]) -> EnrichmentJob:
    """Rebuild EnrichmentJob from a CRM enrichment_jobs API row."""
    proposal_blob = row.get("proposal") or {}
    if not isinstance(proposal_blob, dict):
        proposal_blob = {}
    # Stored either as bare SheetProposal dict or wrapped envelope.
    if "proposal" in proposal_blob and isinstance(proposal_blob["proposal"], dict):
        proposal = proposal_from_dict(proposal_blob["proposal"])
        crm_plan = crm_plan_from_dict(proposal_blob.get("crm_upsert_plan"))
        cancelled = bool(proposal_blob.get("cancelled") or False)
        errors = [str(e) for e in (proposal_blob.get("errors") or [])]
    else:
        proposal = proposal_from_dict(proposal_blob)
        crm_plan = crm_plan_from_dict(proposal_blob.get("crm_upsert_plan"))
        cancelled = False
        errors = []
    return EnrichmentJob(
        proposal=proposal,
        status=str(row.get("status") or "proposed"),
        cells_filled=int(row.get("cells_filled") or 0),
        cells_skipped=int(row.get("cells_skipped") or 0),
        output_path=str(row["output_path"]) if row.get("output_path") else None,
        output_hash=None,
        errors=errors,
        crm_upsert_plan=crm_plan,
        cancelled=cancelled,
    )


def proposal_envelope(
    job: EnrichmentJob,
    *,
    inspection: dict[str, Any] | None = None,
    user_schema: dict[str, Any] | None = None,
    apply_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Envelope stored in crm_enrichment_jobs.proposal_json."""
    return {
        "proposal": job.proposal.to_dict(),
        "crm_upsert_plan": job.crm_upsert_plan.to_dict() if job.crm_upsert_plan else None,
        "cancelled": job.cancelled,
        "errors": list(job.errors),
        "inspection": inspection or {},
        "user_schema": user_schema or {},
        "apply_result": apply_result or {},
        "job_type": "sheet_preprocess",
    }


def estimate_cost(blank_cells: int, proposed_fills: int) -> float:
    """Rough GBP-ish cost estimate for UI (not billing)."""
    # Heuristic: ~0.0002 per blank surveyed + 0.001 per proposed fill.
    return round(blank_cells * 0.0002 + proposed_fills * 0.001, 6)

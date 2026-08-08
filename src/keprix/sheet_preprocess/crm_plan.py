"""Optional CRM upsert plan generation from a sheet proposal (plan only)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from keprix.sheet_preprocess.models import (
    ColumnRole,
    CrmUpsertPlan,
    CrmUpsertRow,
    FillProposal,
    ProvenanceKind,
    SheetProposal,
)


def _role_columns(proposal: SheetProposal, role: ColumnRole) -> list[str]:
    return [name for name, spec in proposal.columns.items() if spec.role == role]


def _cell(frame, row_index: int, column: str | None) -> Any:
    if not column or column not in frame.columns:
        return None
    value = frame.iloc[row_index][column]
    try:
        import pandas as pd

        if bool(pd.isna(value)):
            return None
    except ImportError:
        pass
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _fills_by_row(fills: list[FillProposal]) -> dict[int, dict[str, FillProposal]]:
    by_row: dict[int, dict[str, FillProposal]] = {}
    for fill in fills:
        by_row.setdefault(fill.row_index, {})[fill.column] = fill
    return by_row


def _value_for(
    frame,
    row_index: int,
    column: str | None,
    fills: Mapping[str, FillProposal],
) -> Any:
    if not column:
        return None
    if column in fills:
        return fills[column].value
    return _cell(frame, row_index, column)


def build_crm_upsert_plan(
    frame,
    proposal: SheetProposal,
    *,
    include_fills: bool = True,
    domain_pack: str = "generic",
    source_label: str = "sheet_preprocess",
) -> CrmUpsertPlan:
    """
    Build a CRM upsert plan object from mapped columns and optional fills.

    This does not write to CRM. Callers (Soft Wall / apply path) execute later.
    """
    plan = CrmUpsertPlan(
        sheet_type=proposal.sheet_type,
        source_content_hash=proposal.content_hash,
        mapping_version=proposal.mapping_version,
    )
    if proposal.sheet_type not in {"leads", "generic", "tenant_list", "property_data"}:
        plan.warnings.append(
            f"Sheet type {proposal.sheet_type!r} has no built-in CRM mapping; "
            "plan may be incomplete"
        )

    email_cols = _role_columns(proposal, ColumnRole.CONTACT_EMAIL)
    phone_cols = _role_columns(proposal, ColumnRole.CONTACT_PHONE)
    company_cols = _role_columns(proposal, ColumnRole.COMPANY_NAME)
    identity_cols = _role_columns(proposal, ColumnRole.IDENTITY)
    stage_cols = _role_columns(proposal, ColumnRole.STAGE)
    url_cols = _role_columns(proposal, ColumnRole.URL)
    score_cols = _role_columns(proposal, ColumnRole.SCORE)

    fill_map = _fills_by_row(proposal.fills if include_fills else [])
    row_count = min(len(frame), proposal.analysed_rows or len(frame))

    for row_index in range(row_count):
        fills = fill_map.get(row_index, {})
        company = None
        for col in company_cols:
            company = _value_for(frame, row_index, col, fills)
            if company is not None:
                break
        email = None
        for col in email_cols:
            email = _value_for(frame, row_index, col, fills)
            if email is not None:
                break
        phone = None
        for col in phone_cols:
            phone = _value_for(frame, row_index, col, fills)
            if phone is not None:
                break
        identity = None
        for col in identity_cols:
            identity = _value_for(frame, row_index, col, fills)
            if identity is not None:
                break
        stage = None
        for col in stage_cols:
            stage = _value_for(frame, row_index, col, fills)
            if stage is not None:
                break
        url = None
        for col in url_cols:
            url = _value_for(frame, row_index, col, fills)
            if url is not None:
                break
        scores: dict[str, Any] = {}
        for col in score_cols:
            value = _value_for(frame, row_index, col, fills)
            if value is not None:
                scores[col] = value

        if company is None and email is None and identity is None:
            continue

        account_fields: dict[str, Any] = {
            "domain_pack": domain_pack,
            "source": source_label,
        }
        if company is not None:
            account_fields["name"] = str(company)
            account_fields["company_name"] = str(company)
        if url is not None:
            account_fields["domain"] = str(url)
        if identity is not None:
            account_fields["external_source_id"] = f"sheet:{identity}"

        account_prov = {
            "kind": ProvenanceKind.DERIVED.value
            if row_index in fill_map
            else ProvenanceKind.OBSERVED.value,
            "adapter": source_label,
            "row_index": row_index,
            "content_hash": proposal.content_hash,
        }
        plan.rows.append(
            CrmUpsertRow(
                entity_type="Account",
                action="upsert",
                fields=account_fields,
                row_index=row_index,
                identity_keys={
                    k: v
                    for k, v in {
                        "external_source_id": account_fields.get("external_source_id"),
                        "company_name": account_fields.get("company_name"),
                    }.items()
                    if v is not None
                },
                provenance=account_prov,
            )
        )

        lead_fields: dict[str, Any] = {
            "domain_pack": domain_pack,
            "source": source_label,
            "company_name": account_fields.get("company_name"),
            "name": account_fields.get("company_name") or (str(email) if email else None),
        }
        if email is not None:
            lead_fields["emails"] = [str(email)]
        if phone is not None:
            lead_fields["phones"] = [str(phone)]
        if stage is not None:
            lead_fields["stage"] = str(stage)
        if scores:
            lead_fields["scores"] = scores
        if identity is not None:
            lead_fields["external_source_id"] = f"sheet:{identity}"

        plan.rows.append(
            CrmUpsertRow(
                entity_type="Lead",
                action="upsert",
                fields={k: v for k, v in lead_fields.items() if v is not None},
                row_index=row_index,
                identity_keys={
                    k: v
                    for k, v in {
                        "external_source_id": lead_fields.get("external_source_id"),
                        "email": str(email) if email else None,
                        "company_number": lead_fields.get("company_number"),
                    }.items()
                    if v is not None
                },
                provenance=account_prov,
            )
        )

        if email is not None or phone is not None:
            contact_fields: dict[str, Any] = {
                "domain_pack": domain_pack,
                "source": source_label,
                "emails": [str(email)] if email else [],
                "phones": [str(phone)] if phone else [],
                "name": str(email) if email else str(phone),
            }
            plan.rows.append(
                CrmUpsertRow(
                    entity_type="Contact",
                    action="upsert",
                    fields=contact_fields,
                    row_index=row_index,
                    identity_keys={
                        k: v
                        for k, v in {
                            "email": str(email) if email else None,
                            "phone": str(phone) if phone else None,
                        }.items()
                        if v is not None
                    },
                    provenance=account_prov,
                )
            )

    if not plan.rows:
        plan.warnings.append("No CRM upsert rows could be derived from mapped columns")
    return plan

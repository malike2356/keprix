"""Structured validation for model fill proposals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from keprix.sheet_preprocess.models import (
    ColumnRole,
    ColumnSpec,
    FillProposal,
    IssueSeverity,
    ProvenanceKind,
    ReviewIssue,
)
from keprix.sheet_preprocess.safety import is_blank_cell, looks_like_formula

# Roles that may receive model fills.
FILLABLE_ROLES = frozenset(
    {
        ColumnRole.ENRICH_TARGET,
        ColumnRole.METRIC,
        ColumnRole.SCORE,
        ColumnRole.STAGE,
        ColumnRole.COMPANY_NAME,
        ColumnRole.URL,
        ColumnRole.CONTACT_EMAIL,
        ColumnRole.CONTACT_PHONE,
    }
)

# Contact inventing is blocked unless evidence is present (hardening).
CONTACT_ROLES = frozenset(
    {
        ColumnRole.CONTACT_EMAIL,
        ColumnRole.CONTACT_PHONE,
    }
)


def _coerce_fill(item: Mapping[str, Any], *, row_offset: int = 0) -> FillProposal | ReviewIssue:
    try:
        if "row_index" in item:
            row_index = int(item["row_index"])
        elif "relative_row_index" in item:
            row_index = row_offset + int(item["relative_row_index"])
        else:
            raise KeyError("row_index")
    except (KeyError, TypeError, ValueError):
        return ReviewIssue(
            code="invalid_row_index",
            message="Fill missing or invalid row_index",
            severity=IssueSeverity.ERROR.value,
            detail=dict(item),
        )
    column = item.get("column")
    if not isinstance(column, str) or not column:
        return ReviewIssue(
            code="invalid_column",
            message="Fill missing column name",
            severity=IssueSeverity.ERROR.value,
            row_index=row_index,
            detail=dict(item),
        )
    if "value" not in item:
        return ReviewIssue(
            code="missing_value",
            message="Fill missing value",
            severity=IssueSeverity.ERROR.value,
            row_index=row_index,
            column=column,
        )
    confidence = item.get("confidence")
    try:
        confidence_f = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        return ReviewIssue(
            code="invalid_confidence",
            message="Confidence must be numeric when provided",
            severity=IssueSeverity.ERROR.value,
            row_index=row_index,
            column=column,
        )
    if confidence_f is not None and not (0.0 <= confidence_f <= 1.0):
        return ReviewIssue(
            code="confidence_out_of_range",
            message="Confidence must be between 0 and 1",
            severity=IssueSeverity.ERROR.value,
            row_index=row_index,
            column=column,
        )
    provenance = str(item.get("provenance_kind") or ProvenanceKind.MODEL_INFERRED.value)
    return FillProposal(
        row_index=row_index,
        column=column,
        value=item.get("value"),
        confidence=confidence_f,
        source=str(item.get("source") or "model"),
        evidence=str(item.get("evidence") or ""),
        provenance_kind=provenance,
        adapter=str(item.get("adapter") or "sheet_preprocess"),
        policy_version=str(item.get("policy_version") or "sheet_preprocess.v1"),
        observed_at=str(item["observed_at"]) if item.get("observed_at") else None,
        source_field=str(item["source_field"]) if item.get("source_field") else None,
        verification_state=str(item.get("verification_state") or "unverified"),
    )


def validate_fills(
    fills: Sequence[Mapping[str, Any] | FillProposal],
    *,
    columns: Mapping[str, ColumnSpec],
    frame,
    allowed_columns: Sequence[str] | None = None,
    row_offset: int = 0,
) -> tuple[list[FillProposal], list[ReviewIssue]]:
    """Validate, bound, and deduplicate fills. Invalid items become review issues."""
    allowed = set(allowed_columns) if allowed_columns is not None else {
        name for name, spec in columns.items() if spec.role in FILLABLE_ROLES
    }
    accepted: list[FillProposal] = []
    issues: list[ReviewIssue] = []
    seen: set[tuple[int, str]] = set()

    for raw in fills:
        if isinstance(raw, FillProposal):
            fill = raw
        elif isinstance(raw, Mapping):
            coerced = _coerce_fill(raw, row_offset=row_offset)
            if isinstance(coerced, ReviewIssue):
                issues.append(coerced)
                continue
            fill = coerced
        else:
            issues.append(
                ReviewIssue(
                    code="invalid_fill_type",
                    message="Fill must be a mapping or FillProposal",
                    severity=IssueSeverity.ERROR.value,
                )
            )
            continue

        if fill.column not in columns:
            issues.append(
                ReviewIssue(
                    code="unknown_column",
                    message=f"Column {fill.column!r} is not in the sheet",
                    severity=IssueSeverity.ERROR.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue
        if fill.column not in allowed:
            issues.append(
                ReviewIssue(
                    code="column_not_fillable",
                    message=f"Column {fill.column!r} is not an allowed fill target",
                    severity=IssueSeverity.ERROR.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue
        if fill.row_index < 0 or fill.row_index >= len(frame):
            issues.append(
                ReviewIssue(
                    code="row_out_of_range",
                    message=f"Row index {fill.row_index} is out of range",
                    severity=IssueSeverity.ERROR.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue

        key = (fill.row_index, fill.column)
        if key in seen:
            issues.append(
                ReviewIssue(
                    code="duplicate_fill",
                    message=f"Duplicate fill for row {fill.row_index} column {fill.column}",
                    severity=IssueSeverity.WARNING.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue
        seen.add(key)

        current = frame.iloc[fill.row_index][fill.column]
        if not is_blank_cell(current):
            issues.append(
                ReviewIssue(
                    code="non_empty_cell",
                    message="Refusing to overwrite a non-empty cell",
                    severity=IssueSeverity.WARNING.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue

        if looks_like_formula(fill.value):
            issues.append(
                ReviewIssue(
                    code="formula_value_rejected",
                    message="Fill values must not be spreadsheet formulas",
                    severity=IssueSeverity.ERROR.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue

        role = columns[fill.column].role
        if role in CONTACT_ROLES and not str(fill.evidence or "").strip():
            issues.append(
                ReviewIssue(
                    code="contact_without_evidence",
                    message="Contact email/phone fills require evidence; unknown stays unknown",
                    severity=IssueSeverity.ERROR.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue

        spec = columns[fill.column]
        if spec.allowed_values and str(fill.value) not in spec.allowed_values:
            issues.append(
                ReviewIssue(
                    code="value_not_allowed",
                    message=f"Value {fill.value!r} not in allowed_values",
                    severity=IssueSeverity.ERROR.value,
                    row_index=fill.row_index,
                    column=fill.column,
                )
            )
            continue

        accepted.append(fill)

    return accepted, issues

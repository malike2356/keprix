"""Safe, review-first spreadsheet preprocessing."""

from __future__ import annotations

import re
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from keprix.sheet_preprocess.crm_plan import build_crm_upsert_plan
from keprix.sheet_preprocess.models import (
    ColumnRole,
    ColumnSpec,
    EnrichmentJob,
    FillProposal,
    SheetProposal,
)
from keprix.sheet_preprocess.registry import get_sheet_type_registry
from keprix.sheet_preprocess.safety import (
    ProcessingBudget,
    SheetLimits,
    SheetSafetyError,
    content_hash_file,
    estimate_batch_tokens,
    is_blank_cell,
    load_table_safe,
    write_csv_safe,
)
from keprix.sheet_preprocess.validation import FILLABLE_ROLES, validate_fills

Analyser = Callable[[dict[str, Any]], Mapping[str, Any]]


def _pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "Spreadsheet preprocessing requires pandas; install keprix[analytics]"
        ) from exc
    return pd


def load_table(
    path: str | Path,
    *,
    sheet_name: str | int | None = None,
    header_row: int = 0,
    limits: SheetLimits | None = None,
    delimiter: str | None = None,
):
    """Load CSV, TSV, or XLSX into a dataframe with safety checks."""
    frame, _inspection = load_table_safe(
        path,
        sheet_name=sheet_name,
        header_row=header_row,
        limits=limits,
        delimiter=delimiter,
    )
    return frame


def load_table_with_inspection(
    path: str | Path,
    *,
    sheet_name: str | int | None = None,
    header_row: int = 0,
    limits: SheetLimits | None = None,
    delimiter: str | None = None,
):
    """Load a table and return (frame, SheetInspection)."""
    return load_table_safe(
        path,
        sheet_name=sheet_name,
        header_row=header_row,
        limits=limits,
        delimiter=delimiter,
    )


def write_table(frame, path: str | Path) -> Path:
    """Write a dataframe; CSV paths use formula-injection escaping."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    suffix = destination.suffix.lower()
    if suffix == ".csv":
        return write_csv_safe(frame, destination)
    if suffix in {".xlsx", ".xlsm"}:
        frame.to_excel(destination, index=False, engine="openpyxl")
        return destination
    raise ValueError("Output must use .csv, .xlsx, or .xlsm")


def classify_sheet(columns: Sequence[object]) -> str:
    """Classify a table from normalised column names without assuming a vertical."""
    return get_sheet_type_registry().classify(columns)


def _normalise(name: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _infer_role(name: object) -> ColumnRole:
    normal = _normalise(name)
    if normal in {"email", "email_address", "contact_email", "work_email"}:
        return ColumnRole.CONTACT_EMAIL
    if normal in {"phone", "telephone", "mobile", "contact_phone", "phone_number"}:
        return ColumnRole.CONTACT_PHONE
    if normal in {"company", "company_name", "organisation", "organization", "business_name"}:
        return ColumnRole.COMPANY_NAME
    if normal in {"url", "website", "domain", "profile_url", "linkedin_url"}:
        return ColumnRole.URL
    if normal in {"stage", "status", "pipeline_stage", "lifecycle_stage"}:
        return ColumnRole.STAGE
    if normal.endswith("score") or normal in {"score", "rating", "rank"}:
        return ColumnRole.SCORE
    if normal in {"id", "uuid", "reference", "ref", "record_id", "lead_id"}:
        return ColumnRole.IDENTITY
    if any(token in normal for token in ("email", "phone", "name", "address", "postcode")):
        return ColumnRole.PII
    return ColumnRole.METRIC


def _spec_from_mapping(name: str, supplied: Mapping[str, Any]) -> ColumnSpec:
    role = ColumnRole(str(supplied.get("role", "metric")))
    allowed = supplied.get("allowed_values") or ()
    if isinstance(allowed, str):
        allowed_values = (allowed,)
    else:
        allowed_values = tuple(str(item) for item in allowed)
    return ColumnSpec(
        name=name,
        role=role,
        metric=str(supplied.get("metric") or "") or None,
        data_type=str(supplied.get("data_type") or supplied.get("type") or "text"),
        description=str(supplied.get("description") or ""),
        confidence=1.0,
        source="user",
        units=str(supplied["units"]) if supplied.get("units") is not None else None,
        currency=str(supplied["currency"]) if supplied.get("currency") is not None else None,
        timezone=str(supplied["timezone"]) if supplied.get("timezone") is not None else None,
        allowed_values=allowed_values,
        validation=str(supplied["validation"]) if supplied.get("validation") is not None else None,
        required=bool(supplied.get("required") or False),
        unique_key=bool(supplied.get("unique_key") or False),
        metric_formula=str(supplied["metric_formula"])
        if supplied.get("metric_formula") is not None
        else None,
        pii_class=str(supplied["pii_class"]) if supplied.get("pii_class") is not None else None,
    )


def analyse_columns(
    columns: Sequence[object],
    user_schema: Mapping[str, str | ColumnRole | Mapping[str, Any]] | None = None,
) -> dict[str, ColumnSpec]:
    """Build column specifications, giving an explicit user schema priority."""
    schema = user_schema or {}
    result: dict[str, ColumnSpec] = {}
    for raw_name in columns:
        name = str(raw_name)
        supplied = schema.get(name)
        if isinstance(supplied, Mapping):
            result[name] = _spec_from_mapping(name, supplied)
        elif supplied is not None:
            result[name] = ColumnSpec(name=name, role=ColumnRole(str(supplied)), source="user")
        else:
            result[name] = ColumnSpec(
                name=name,
                role=_infer_role(name),
                confidence=0.65,
                source="heuristic",
            )
    unknown = sorted(set(schema) - set(result))
    if unknown:
        raise ValueError(f"Schema references missing columns: {', '.join(unknown)}")
    return result


def _is_blank(value: Any) -> bool:
    return is_blank_cell(value)


def apply_proposal(frame, fills: Sequence[FillProposal]) -> tuple[Any, int, int]:
    """Apply reviewed fills to blank cells only and return frame, applied, skipped."""
    output = frame.copy(deep=True)
    applied = 0
    skipped = 0
    for fill in fills:
        if fill.row_index < 0 or fill.row_index >= len(output) or fill.column not in output.columns:
            skipped += 1
            continue
        current = output.iloc[fill.row_index][fill.column]
        if not _is_blank(current):
            skipped += 1
            continue
        output.at[output.index[fill.row_index], fill.column] = fill.value
        applied += 1
    return output, applied, skipped


def count_blank_cells(frame) -> int:
    total = 0
    for column in frame.columns:
        for value in frame[column].tolist():
            if is_blank_cell(value):
                total += 1
    return total


class SheetPreprocessor:
    """Create inspectable proposals and apply them only after caller approval."""

    def __init__(
        self,
        analyser: Analyser | None = None,
        *,
        max_rows: int = 500,
        batch_size: int = 50,
        limits: SheetLimits | None = None,
        max_tokens: int = 200_000,
    ):
        if max_rows < 1 or batch_size < 1:
            raise ValueError("max_rows and batch_size must be positive")
        self.analyser = analyser
        self.max_rows = max_rows
        self.batch_size = batch_size
        self.limits = limits or SheetLimits()
        self.max_tokens = max_tokens
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        """Signal cancellation; stops further model batch calls."""
        self._cancel.set()

    def clear_cancel(self) -> None:
        self._cancel.clear()

    def propose(
        self,
        frame,
        *,
        user_schema: Mapping[str, str | ColumnRole | Mapping[str, Any]] | None = None,
        metrics: Sequence[str] | None = None,
        context: str = "",
        content_hash: str | None = None,
        selected_worksheet: str | int | None = None,
        header_row: int = 0,
        flattened_export: bool = False,
        sheet_warnings: Sequence[str] | None = None,
        resume_from: EnrichmentJob | None = None,
        build_crm_plan: bool = False,
        domain_pack: str = "generic",
    ) -> EnrichmentJob:
        """
        Propose column roles and optional fills.

        Modes:
        - user_schema: caller supplies column->role map (and optional metrics).
        - auto_analyse: heuristics (+ optional model) propose type and roles.

        Never mutates ``frame``. Apply separately after review.
        """
        mode = "user_schema" if user_schema else "auto_analyse"
        if resume_from is not None and resume_from.proposal.mode:
            mode = resume_from.proposal.mode
            columns = resume_from.proposal.columns
            proposal = resume_from.proposal
            job = resume_from
            if job.status not in {"proposed", "partial"}:
                raise ValueError(f"Cannot resume job in status {job.status!r}")
        else:
            columns = analyse_columns(frame.columns, user_schema)
            blanks = count_blank_cells(frame)
            proposal = SheetProposal(
                sheet_type=classify_sheet(frame.columns),
                columns=columns,
                row_count=len(frame),
                blank_cells=blanks,
                analysed_rows=min(len(frame), self.max_rows),
                mode=mode,
                content_hash=content_hash,
                selected_worksheet=selected_worksheet,
                header_row=header_row,
                flattened_export=flattened_export,
            )
            if flattened_export:
                proposal.warnings.append(
                    "Flattened data export: original workbook structure, formulas, "
                    "charts, and formatting are not preserved"
                )
            if sheet_warnings:
                proposal.warnings.extend(str(item) for item in sheet_warnings)
            job = EnrichmentJob(proposal=proposal)

        requested_metrics = [str(metric) for metric in metrics or []]
        proposal.missing_metrics = [
            metric for metric in requested_metrics if metric not in frame.columns
        ]
        if len(frame) > self.max_rows:
            warning = (
                f"Analysis limited to {self.max_rows} of {len(frame)} rows; "
                "remaining rows were not sent to a model"
            )
            if warning not in proposal.warnings:
                proposal.warnings.append(warning)

        if self.analyser is None:
            if "No model analyser configured; returning schema proposal only" not in proposal.warnings:
                proposal.warnings.append(
                    "No model analyser configured; returning schema proposal only"
                )
            if build_crm_plan:
                job.crm_upsert_plan = build_crm_upsert_plan(
                    frame, proposal, domain_pack=domain_pack
                )
            return job

        target_columns = [
            name for name, spec in columns.items() if spec.role in FILLABLE_ROLES
        ]
        budget = ProcessingBudget(
            max_processing_seconds=self.limits.max_processing_seconds,
            max_tokens=self.max_tokens,
        )
        if resume_from is not None:
            budget.tokens_used = proposal.checkpoint.tokens_used
            start_row = proposal.checkpoint.next_row
        else:
            start_row = 0

        for start in range(start_row, proposal.analysed_rows, self.batch_size):
            if self._cancel.is_set() or job.cancelled:
                job.cancelled = True
                proposal.checkpoint.cancelled = True
                proposal.warnings.append(
                    f"Cancelled before batch starting at row {start}; partial proposal retained"
                )
                job.status = "cancelled"
                break

            stop = min(start + self.batch_size, proposal.analysed_rows)
            estimated = estimate_batch_tokens(stop - start, len(frame.columns))
            try:
                budget.check(estimated_tokens=estimated)
            except SheetSafetyError as exc:
                proposal.warnings.append(f"Budget stop at row {start}: {exc}")
                job.status = "partial"
                break

            payload = {
                "sheet_type": proposal.sheet_type,
                "context": context[:2000],
                "columns": {name: spec.role.value for name, spec in columns.items()},
                "target_columns": target_columns,
                "rows": frame.iloc[start:stop]
                .where(frame.iloc[start:stop].notna(), None)
                .to_dict("records"),
                "row_offset": start,
                "rules": {
                    "empty_cells_only": True,
                    "return_evidence": True,
                    "never_evaluate_formulas": True,
                },
            }
            try:
                response = self.analyser(payload)
                tokens = int(response.get("tokens_used") or estimated)
                budget.record_tokens(tokens)
                proposal.checkpoint.tokens_used = budget.tokens_used
                accepted, issues = validate_fills(
                    list(response.get("fills") or []),
                    columns=columns,
                    frame=frame,
                    allowed_columns=target_columns,
                    row_offset=start,
                )
                proposal.fills.extend(accepted)
                proposal.issues.extend(issues)
                proposal.checkpoint.next_row = stop
                proposal.checkpoint.batches_completed += 1
            except Exception as exc:
                proposal.warnings.append(f"Batch {start}:{stop} failed: {exc}")
                proposal.checkpoint.next_row = stop
                proposal.checkpoint.batches_completed += 1
                # Fail soft: keep going with remaining batches.
                continue

        if job.status == "proposed" and proposal.checkpoint.next_row < proposal.analysed_rows:
            job.status = "partial"
        elif job.status == "proposed" and proposal.issues and not proposal.fills:
            job.status = "proposed"

        if build_crm_plan:
            job.crm_upsert_plan = build_crm_upsert_plan(
                frame, proposal, domain_pack=domain_pack
            )
        return job

    def propose_from_path(
        self,
        path: str | Path,
        *,
        sheet_name: str | int | None = None,
        header_row: int = 0,
        delimiter: str | None = None,
        user_schema: Mapping[str, str | ColumnRole | Mapping[str, Any]] | None = None,
        metrics: Sequence[str] | None = None,
        context: str = "",
        build_crm_plan: bool = False,
        domain_pack: str = "generic",
    ) -> tuple[Any, EnrichmentJob]:
        """Load with safety checks, then propose without mutating the source file."""
        frame, inspection = load_table_with_inspection(
            path,
            sheet_name=sheet_name,
            header_row=header_row,
            limits=self.limits,
            delimiter=delimiter,
        )
        job = self.propose(
            frame,
            user_schema=user_schema,
            metrics=metrics,
            context=context,
            content_hash=inspection.content_hash,
            selected_worksheet=inspection.selected_worksheet
            if sheet_name is None
            else sheet_name,
            header_row=header_row,
            flattened_export=inspection.flattened_export,
            sheet_warnings=inspection.warnings,
            build_crm_plan=build_crm_plan,
            domain_pack=domain_pack,
        )
        return frame, job

    def apply(
        self,
        frame,
        job: EnrichmentJob,
        *,
        output_path: str | Path | None = None,
        build_crm_plan: bool = False,
        domain_pack: str = "generic",
    ) -> EnrichmentJob:
        if job.status not in {"proposed", "partial"}:
            raise ValueError(f"Job cannot be applied from status {job.status!r}")
        if job.cancelled:
            raise ValueError("Cancelled job cannot be applied")
        output, applied, skipped = apply_proposal(frame, job.proposal.fills)
        job.cells_filled = applied
        job.cells_skipped = skipped
        job.status = "applied"
        if output_path is not None:
            written = write_table(output, output_path)
            job.output_path = str(written)
            job.output_hash = content_hash_file(written)
            if job.proposal.flattened_export or Path(written).suffix.lower() == ".csv":
                warning = (
                    "Applied output is a flattened data export; original workbook "
                    "artifacts were not preserved"
                )
                if warning not in job.proposal.warnings:
                    job.proposal.warnings.append(warning)
        if build_crm_plan:
            # Plan only; never writes CRM here.
            job.crm_upsert_plan = build_crm_upsert_plan(
                output, job.proposal, domain_pack=domain_pack
            )
        return job

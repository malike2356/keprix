"""Spreadsheet / row-array readers for CRM lead ingestion."""

from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path
from typing import Any

from keprix.sheet_preprocess.safety import (
    SheetLimits,
    SheetSafetyError,
    content_hash_bytes,
    content_hash_file,
    decode_csv_bytes,
    detect_csv_delimiter,
    enforce_file_limits,
    load_table_safe,
    sanitize_loaded_formulas,
    validate_frame_shape,
)

SUPPORTED_INGEST_SUFFIXES = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".ods"})


def reject_path_traversal(path: str | Path) -> Path:
    """Reject relative path traversal before resolve."""
    raw = Path(path)
    if ".." in raw.parts:
        raise SheetSafetyError("Path traversal rejected")
    text = str(path)
    if ".." in Path(text).as_posix().split("/"):
        raise SheetSafetyError("Path traversal rejected")
    return raw.expanduser()


def _frame_to_rows(frame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    columns = [str(c) for c in frame.columns]
    for _, series in frame.iterrows():
        row: dict[str, Any] = {}
        for col in columns:
            value = series[col]
            try:
                import pandas as pd

                if bool(pd.isna(value)):
                    value = None
            except Exception:
                pass
            row[col] = value
        rows.append(row)
    return rows


def read_rows_list(rows: list[dict[str, Any]], *, limits: SheetLimits | None = None) -> dict[str, Any]:
    """Accept already-normalized row arrays (Google Sheets / agent tools / paste)."""
    limits = limits or SheetLimits()
    if not isinstance(rows, list):
        raise SheetSafetyError("rows must be a list of dicts")
    if len(rows) > limits.max_rows:
        raise SheetSafetyError(f"Row count {len(rows)} exceeds limit {limits.max_rows}")
    clean: list[dict[str, Any]] = []
    max_cols = 0
    for item in rows:
        if not isinstance(item, dict):
            raise SheetSafetyError("Each row must be a dict")
        max_cols = max(max_cols, len(item))
        if max_cols > limits.max_columns:
            raise SheetSafetyError(
                f"Column count {max_cols} exceeds limit {limits.max_columns}"
            )
        clean.append(dict(item))
    return {
        "rows": clean,
        "format": "rows",
        "content_hash": content_hash_bytes(repr(clean).encode("utf-8")),
        "warnings": [],
        "inspection": None,
    }


def read_path(
    path: str | Path,
    *,
    sheet_name: str | int | None = None,
    header_row: int = 0,
    limits: SheetLimits | None = None,
) -> dict[str, Any]:
    limits = limits or SheetLimits()
    source = reject_path_traversal(path)
    if not source.is_file():
        # resolve after traversal check
        try:
            source = source.resolve(strict=True)
        except FileNotFoundError as exc:
            raise SheetSafetyError(f"Spreadsheet not found: {path}") from exc
    else:
        source = source.resolve()

    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_INGEST_SUFFIXES:
        raise SheetSafetyError(f"Unsupported spreadsheet format: {suffix or '(none)'}")

    if suffix in {".csv", ".tsv", ".xlsx"}:
        frame, inspection = load_table_safe(
            source,
            sheet_name=sheet_name,
            header_row=header_row,
            limits=limits,
        )
        return {
            "rows": _frame_to_rows(frame),
            "format": suffix.lstrip("."),
            "content_hash": inspection.content_hash,
            "warnings": list(inspection.warnings),
            "inspection": inspection,
            "path": str(source),
        }

    # .xls / .ods via pandas engines (xlrd / odf)
    inspection = enforce_file_limits(source, limits)
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "Spreadsheet ingestion requires pandas; install keprix[analytics]"
        ) from exc

    warnings = list(inspection.warnings)
    if suffix == ".xls":
        try:
            import xlrd  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "Legacy .xls requires xlrd; install keprix[analytics]"
            ) from exc
        frame = pd.read_excel(
            source,
            sheet_name=sheet_name if sheet_name is not None else 0,
            header=header_row,
            engine="xlrd",
            dtype=object,
        )
    elif suffix == ".ods":
        try:
            import odf  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "ODS requires odfpy; install keprix[analytics]"
            ) from exc
        frame = pd.read_excel(
            source,
            sheet_name=sheet_name if sheet_name is not None else 0,
            header=header_row,
            engine="odf",
            dtype=object,
        )
    else:
        raise SheetSafetyError(f"Unsupported spreadsheet format: {suffix}")

    if isinstance(frame, dict):
        # Multi-sheet without selection
        raise SheetSafetyError(
            "Worksheet selection required for multi-sheet workbook: "
            + ", ".join(str(k) for k in frame.keys())
        )

    validate_frame_shape(frame, limits)
    frame, formula_count = sanitize_loaded_formulas(frame)
    if formula_count:
        warnings.append(
            f"Detected {formula_count} formula cell(s); values kept as text and never evaluated"
        )
    return {
        "rows": _frame_to_rows(frame),
        "format": suffix.lstrip("."),
        "content_hash": content_hash_file(source),
        "warnings": warnings,
        "inspection": inspection,
        "path": str(source),
    }


def read_bytes(
    payload: bytes,
    *,
    filename: str = "upload.csv",
    sheet_name: str | int | None = None,
    header_row: int = 0,
    limits: SheetLimits | None = None,
) -> dict[str, Any]:
    limits = limits or SheetLimits()
    if len(payload) > limits.max_bytes:
        raise SheetSafetyError(
            f"File exceeds size limit ({len(payload)} bytes > {limits.max_bytes} bytes)"
        )
    name = Path(filename).name
    if ".." in name or "/" in name or "\\" in name:
        raise SheetSafetyError("Path traversal rejected in filename")
    suffix = Path(name).suffix.lower() or ".csv"
    if suffix not in SUPPORTED_INGEST_SUFFIXES:
        raise SheetSafetyError(f"Unsupported spreadsheet format: {suffix}")

    if suffix in {".csv", ".tsv"}:
        text, encoding = decode_csv_bytes(payload)
        delimiter = "\t" if suffix == ".tsv" else detect_csv_delimiter(text)
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = [dict(r) for r in reader]
        if len(rows) > limits.max_rows:
            raise SheetSafetyError(f"Row count {len(rows)} exceeds limit {limits.max_rows}")
        cols = len(reader.fieldnames or [])
        if cols > limits.max_columns:
            raise SheetSafetyError(f"Column count {cols} exceeds limit {limits.max_columns}")
        return {
            "rows": rows,
            "format": suffix.lstrip("."),
            "content_hash": content_hash_bytes(payload),
            "warnings": [],
            "inspection": None,
            "encoding": encoding,
            "delimiter": delimiter,
        }

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(payload)
        tmp = Path(handle.name)
    try:
        result = read_path(
            tmp,
            sheet_name=sheet_name,
            header_row=header_row,
            limits=limits,
        )
        result["content_hash"] = content_hash_bytes(payload)
        result["filename"] = name
        return result
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

"""Dataset and codebook exports."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Literal

from keprix.research_workspace.datasets.codebook import Codebook
from keprix.research_workspace.datasets.missing_values import apply_missing_codes

ExportFormat = Literal[
    "csv",
    "parquet",
    "json-schema",
    "pspp",
    "r",
    "python",
    "jamovi",
]


def export_dataset(
    *,
    data_path: Path,
    codebook: Codebook,
    fmt: ExportFormat,
    dest_dir: Path,
) -> dict[str, Any]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    columns, rows = _read_csv(data_path)
    rows = apply_missing_codes(rows, codebook)
    if fmt == "csv":
        out = dest_dir / f"{codebook.dataset_id}-clean.csv"
        _write_csv(out, columns, rows, codebook)
        return {"path": str(out), "format": fmt}
    if fmt == "json-schema":
        out = dest_dir / f"{codebook.dataset_id}.schema.json"
        out.write_text(json.dumps(_json_schema(codebook), indent=2), encoding="utf-8")
        return {"path": str(out), "format": fmt}
    if fmt == "pspp":
        out = dest_dir / f"{codebook.dataset_id}.sps"
        workspace_root = dest_dir.parent.parent.parent
        out.write_text(_pspp_syntax(codebook, data_path, workspace_root), encoding="utf-8")
        return {"path": str(out), "format": fmt}
    if fmt == "r":
        out = dest_dir / f"{codebook.dataset_id}.R"
        out.write_text(_r_script(codebook, data_path), encoding="utf-8")
        return {"path": str(out), "format": fmt}
    if fmt == "python":
        out = dest_dir / f"{codebook.dataset_id}-cell.py"
        out.write_text(_python_cell(codebook, data_path), encoding="utf-8")
        return {"path": str(out), "format": fmt}
    if fmt == "jamovi":
        csv_out = dest_dir / f"{codebook.dataset_id}-jamovi.csv"
        notes_out = dest_dir / f"{codebook.dataset_id}-jamovi-notes.md"
        _write_csv(csv_out, columns, rows, codebook)
        notes_out.write_text(_jamovi_notes(codebook), encoding="utf-8")
        return {"path": str(csv_out), "notes_path": str(notes_out), "format": fmt}
    if fmt == "parquet":
        out = dest_dir / f"{codebook.dataset_id}.parquet"
        try:
            import pyarrow as pa
            import pyarrow.csv as pacsv
        except ImportError as exc:
            raise ImportError("Parquet export requires pyarrow; pip install pyarrow") from exc
        temp_csv = dest_dir / f"{codebook.dataset_id}-tmp.csv"
        _write_csv(temp_csv, columns, rows, codebook)
        table = pacsv.read_csv(temp_csv)
        pa.parquet.write_table(table, out)
        temp_csv.unlink(missing_ok=True)
        return {"path": str(out), "format": fmt}
    raise ValueError(f"Unsupported export format: {fmt}")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return columns, rows


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]], codebook: Codebook) -> None:
    label_map = {variable.name: variable.label for variable in codebook.variables}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writerow({column: label_map.get(column, column) for column in columns})
        writer.writerow({column: column for column in columns})
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _json_schema(codebook: Codebook) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for variable in codebook.variables:
        properties[variable.name] = {
            "title": variable.label or variable.name,
            "type": "number" if variable.var_type == "numeric" else "string",
            "measurementLevel": variable.measurement_level,
            "enum": list(variable.value_labels.keys()) or None,
            "missingValues": variable.missing_codes,
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "dataset_id": codebook.dataset_id,
        "version_id": codebook.version_id,
        "variables": [variable.to_dict() for variable in codebook.variables],
        "properties": properties,
    }


def _pspp_syntax(codebook: Codebook, data_path: Path, workspace_root: Path) -> str:
    from keprix.research_workspace.stats.pspp.syntax import generate_analysis_syntax

    return generate_analysis_syntax(
        codebook=codebook,
        data_path=data_path,
        workspace_root=workspace_root,
        procedures=[{"type": "frequencies", "variables": [variable.name for variable in codebook.variables[:5]]}],
    )


def _r_script(codebook: Codebook, data_path: Path) -> str:
    labels = ", ".join(f'"{variable.name}" = "{variable.label}"' for variable in codebook.variables if variable.label)
    return (
        "# Generated by keprix dataset manager\n"
        f"df <- read.csv('{data_path.as_posix()}', stringsAsFactors = FALSE)\n"
        f"var_labels <- c({labels})\n"
        "attr(df, 'keprix_codebook') <- var_labels\n"
        "df\n"
    )


def _python_cell(codebook: Codebook, data_path: Path) -> str:
    return (
        "# Generated by keprix dataset manager\n"
        "import pandas as pd\n"
        f"df = pd.read_csv('{data_path.as_posix()}')\n"
        f"codebook = {json.dumps(codebook.to_dict(), indent=2)}\n"
        "df\n"
    )


def _jamovi_notes(codebook: Codebook) -> str:
    lines = ["# jamovi import notes", "", "Import the paired CSV with variable labels in row 1 and names in row 2.", ""]
    for variable in codebook.variables:
        lines.append(f"- `{variable.name}`: {variable.label or variable.name} ({variable.measurement_level})")
        if variable.value_labels:
            labels = ", ".join(f"{key}={value}" for key, value in variable.value_labels.items())
            lines.append(f"  - value labels: {labels}")
        if variable.missing_codes:
            lines.append(f"  - missing codes: {', '.join(variable.missing_codes)}")
    return "\n".join(lines) + "\n"

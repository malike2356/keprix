"""Versioned dataset transforms."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from keprix.research_workspace.datasets.codebook import Codebook, VariableDefinition
from keprix.research_workspace.datasets.lineage import LineageStore
from keprix.research_workspace.datasets.missing_values import apply_missing_codes


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return columns, rows


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def apply_transform(
    *,
    source_csv: Path,
    dest_csv: Path,
    codebook: Codebook,
    transform: str,
    params: dict[str, Any],
    dataset_id: str,
    version_number: int,
    lineage_store: LineageStore,
) -> Codebook:
    columns, rows = _read_csv(source_csv)
    updated_codebook = Codebook(
        dataset_id=codebook.dataset_id,
        version_id=codebook.version_id,
        notes=codebook.notes,
        variables=[VariableDefinition.from_dict(variable.to_dict()) for variable in codebook.variables],
    )
    if transform == "apply_missing":
        rows = apply_missing_codes(rows, updated_codebook)
    elif transform == "rename_column":
        old_name = str(params["from"])
        new_name = str(params["to"])
        rows = [{(new_name if key == old_name else key): value for key, value in row.items()} for row in rows]
        columns = [new_name if column == old_name else column for column in columns]
        for variable in updated_codebook.variables:
            if variable.name == old_name:
                variable.name = new_name
                variable.source_column = new_name
    elif transform == "recode_values":
        column = str(params["column"])
        mapping = {str(key): str(value) for key, value in (params.get("mapping") or {}).items()}
        for row in rows:
            if column in row and str(row[column]) in mapping:
                row[column] = mapping[str(row[column])]
    elif transform == "derive_column":
        name = str(params["name"])
        expression = str(params.get("expression") or "")
        columns.append(name)
        for row in rows:
            row[name] = expression
        updated_codebook.variables.append(
            VariableDefinition(
                name=name,
                label=str(params.get("label") or name),
                var_type="string",
                measurement_level="nominal",
                derived_expression=expression,
            )
        )
    else:
        raise ValueError(f"Unsupported transform: {transform}")
    cleaned_rows = apply_missing_codes(rows, updated_codebook)
    _write_csv(dest_csv, columns, cleaned_rows)
    lineage_store.append_step(dataset_id, version_number, transform, **params)
    return updated_codebook

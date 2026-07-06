"""Missing value handling."""

from __future__ import annotations

from typing import Any

from keprix.research_workspace.datasets.codebook import Codebook, VariableDefinition

DEFAULT_MISSING_CODES = ("", "NA", "N/A", "null", ".", "-99", "-999")


def normalize_missing(value: Any, missing_codes: list[str] | None = None) -> Any:
    codes = set(missing_codes or DEFAULT_MISSING_CODES)
    text = "" if value is None else str(value).strip()
    if text in codes:
        return None
    return value


def apply_missing_codes(rows: list[dict[str, Any]], codebook: Codebook) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    variable_map = {variable.name: variable for variable in codebook.variables}
    for row in rows:
        cleaned_row: dict[str, Any] = {}
        for key, value in row.items():
            variable = variable_map.get(key)
            missing_codes = variable.missing_codes if variable else list(DEFAULT_MISSING_CODES)
            cleaned_row[key] = normalize_missing(value, missing_codes)
        cleaned.append(cleaned_row)
    return cleaned


def merge_missing_codes(variable: VariableDefinition, codes: list[str]) -> VariableDefinition:
    merged = list(dict.fromkeys([*variable.missing_codes, *codes]))
    variable.missing_codes = merged
    return variable

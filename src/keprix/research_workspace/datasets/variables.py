"""Variable inference helpers."""

from __future__ import annotations

import re
from typing import Any

from keprix.research_workspace.datasets.codebook import VariableDefinition

_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")


def infer_type(values: list[Any]) -> str:
    non_empty = [value for value in values if value not in (None, "")]
    if not non_empty:
        return "string"
    if all(_NUMERIC_RE.match(str(value)) for value in non_empty):
        return "numeric"
    return "string"


def infer_measurement_level(var_type: str, distinct_count: int) -> str:
    if var_type == "numeric":
        return "scale"
    if distinct_count <= 10:
        return "ordinal"
    return "nominal"


def build_variables_from_columns(
    columns: list[str],
    rows: list[dict[str, Any]],
    *,
    labels: dict[str, str] | None = None,
    value_labels: dict[str, dict[str, str]] | None = None,
) -> list[VariableDefinition]:
    variables: list[VariableDefinition] = []
    labels = labels or {}
    value_labels = value_labels or {}
    for column in columns:
        values = [row.get(column) for row in rows]
        var_type = infer_type(values)
        distinct = {str(value) for value in values if value not in (None, "")}
        variables.append(
            VariableDefinition(
                name=column,
                label=labels.get(column, column),
                var_type=var_type,
                measurement_level=infer_measurement_level(var_type, len(distinct)),
                value_labels=value_labels.get(column, {}),
                source_column=column,
            )
        )
    return variables

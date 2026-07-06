"""Dataset metadata for jamovi export."""

from __future__ import annotations

from typing import Any


def build_metadata(
    columns: list[dict[str, Any]],
    *,
    dataset_name: str = "dataset",
) -> dict[str, Any]:
    variables = []
    for column in columns:
        variables.append(
            {
                "name": column["name"],
                "label": column.get("label", column["name"]),
                "measurement_level": column.get("measurement_level", "scale"),
                "value_labels": column.get("value_labels", {}),
                "missing_notes": column.get("missing_notes", ""),
            }
        )
    return {"dataset_name": dataset_name, "variables": variables}

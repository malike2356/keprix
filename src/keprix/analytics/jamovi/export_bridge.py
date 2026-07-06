"""jamovi export bridge."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any

from keprix.analytics.jamovi.metadata import build_metadata


def prepare_export_package(
    rows: list[dict[str, Any]],
    *,
    columns: list[dict[str, Any]] | None = None,
    dataset_name: str = "dataset",
    suggested_analyses: list[str] | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("rows are required")
    fieldnames = list(columns or [{"name": key} for key in rows[0].keys()])
    names = [col["name"] if isinstance(col, dict) else str(col) for col in fieldnames]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=names, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in names})
    metadata = build_metadata(
        [col if isinstance(col, dict) else {"name": str(col)} for col in fieldnames],
        dataset_name=dataset_name,
    )
    instructions = [
        "Import data.csv into jamovi.",
        "Apply variable labels from metadata.json.",
        "Review measurement levels before running analyses.",
    ]
    package_bytes = _zip_package(
        {
            "data.csv": buffer.getvalue(),
            "metadata.json": json.dumps(metadata, indent=2),
            "instructions.txt": "\n".join(instructions) + "\n",
        }
    )
    return {
        "dataset_name": dataset_name,
        "csv": buffer.getvalue(),
        "metadata": metadata,
        "suggested_analyses": suggested_analyses or ["descriptives", "regression"],
        "instructions": instructions,
        "package_bytes": package_bytes,
        "package_filename": f"{dataset_name}-jamovi.zip",
    }


def _zip_package(files: dict[str, str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return out.getvalue()

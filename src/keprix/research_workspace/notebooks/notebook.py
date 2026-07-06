"""Notebook document helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from keprix.research_workspace.schemas import new_trace_id


def build_provenance(
    *,
    project_id: str,
    dataset_id: str | None = None,
    dataset_version: int | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "trace_id": trace_id or new_trace_id(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_notebook(
    *,
    code_cells: list[str],
    markdown_cells: list[str] | None = None,
    runtime: Literal["python", "r"] = "python",
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    if provenance:
        cells.append(
            {
                "cell_type": "markdown",
                "source": [
                    "# Keprix research notebook\n",
                    f"Trace: `{provenance.get('trace_id')}`\n",
                    f"Dataset: `{provenance.get('dataset_id')}` v{provenance.get('dataset_version')}\n",
                ],
                "metadata": {"keprix": provenance},
            }
        )
    for text in markdown_cells or []:
        cells.append({"cell_type": "markdown", "source": text.splitlines(True), "metadata": {}})
    for code in code_cells:
        cells.append({"cell_type": "code", "source": code.splitlines(True), "metadata": {}, "outputs": []})
    kernel = "ir" if runtime == "r" else "python3"
    display = "R" if runtime == "r" else "Python 3"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"name": kernel, "display_name": display},
            "keprix": provenance or {},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def attach_cell_output(
    notebook: dict[str, Any],
    *,
    cell_index: int,
    stdout: str,
    stderr: str,
    return_code: int,
    repair_suggestions: list[str],
) -> dict[str, Any]:
    cells = notebook.get("cells") or []
    if cell_index < 0 or cell_index >= len(cells):
        return notebook
    outputs: list[dict[str, Any]] = []
    if stdout:
        outputs.append({"output_type": "stream", "name": "stdout", "text": stdout.splitlines(True)})
    if stderr:
        outputs.append({"output_type": "stream", "name": "stderr", "text": stderr.splitlines(True)})
    if return_code != 0:
        outputs.append(
            {
                "output_type": "error",
                "ename": "ExecutionError",
                "evalue": f"exit code {return_code}",
                "traceback": repair_suggestions,
            }
        )
    cells[cell_index]["outputs"] = outputs
    notebook["cells"] = cells
    return notebook


def export_script(notebook: dict[str, Any], *, runtime: Literal["python", "r"] = "python") -> str:
    lines: list[str] = []
    for cell in notebook.get("cells") or []:
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source") or []
        if isinstance(source, str):
            lines.append(source)
        else:
            lines.extend(source)
        if runtime == "python":
            lines.append("\n")
    return "".join(lines)

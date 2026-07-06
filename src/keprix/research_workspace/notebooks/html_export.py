"""HTML export for notebooks."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def notebook_to_html(notebook: dict[str, Any]) -> str:
    provenance = (notebook.get("metadata") or {}).get("keprix") or {}
    parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>Keprix notebook report</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;}",
        "pre{background:#f4f4f4;padding:1rem;overflow:auto;}",
        ".cell{margin-bottom:1.5rem;border-bottom:1px solid #ddd;padding-bottom:1rem;}",
        ".meta{color:#555;font-size:0.9rem;}</style></head><body>",
        "<h1>Keprix notebook report</h1>",
        f"<p class='meta'>Trace: {html.escape(str(provenance.get('trace_id', '')))} | "
        f"Dataset: {html.escape(str(provenance.get('dataset_id', '')))} "
        f"v{html.escape(str(provenance.get('dataset_version', '')))}</p>",
    ]
    for index, cell in enumerate(notebook.get("cells") or []):
        cell_type = cell.get("cell_type")
        parts.append(f"<section class='cell'><h2>Cell {index + 1} ({html.escape(cell_type or '')})</h2>")
        source = cell.get("source") or []
        if isinstance(source, str):
            text = source
        else:
            text = "".join(source)
        parts.append(f"<pre>{html.escape(text)}</pre>")
        for output in cell.get("outputs") or []:
            if output.get("output_type") == "stream":
                stream = "".join(output.get("text") or [])
                parts.append(f"<pre><strong>{html.escape(output.get('name', 'out'))}</strong>\n{html.escape(stream)}</pre>")
            if output.get("output_type") == "error":
                traceback_text = "\n".join(output.get("traceback") or [])
                parts.append(
                    "<pre class='error'>"
                    f"{html.escape(output.get('ename', 'Error'))}: {html.escape(str(output.get('evalue', '')))}\n"
                    f"{html.escape(traceback_text)}"
                    "</pre>"
                )
        parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


def write_html_report(notebook: dict[str, Any], dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(notebook_to_html(notebook), encoding="utf-8")
    return str(dest)


def write_ipynb(notebook: dict[str, Any], dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    return str(dest)

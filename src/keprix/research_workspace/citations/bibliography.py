"""Bibliography export formats."""

from __future__ import annotations

import json
from typing import Any, Literal

from keprix.research_workspace.citations.bibtex import record_to_bibtex
from keprix.research_workspace.citations.csl import records_to_csl_json
from keprix.research_workspace.citations.models import CitationRecord

ExportFormat = Literal["bibtex", "csl-json", "markdown", "report"]


def export_bibliography(records: list[CitationRecord], fmt: ExportFormat) -> str:
    if fmt == "bibtex":
        return "\n\n".join(record_to_bibtex(record) for record in records)
    if fmt == "csl-json":
        return json.dumps(records_to_csl_json(records), indent=2)
    if fmt == "markdown":
        return _markdown_references(records)
    if fmt == "report":
        return _report_section(records)
    raise ValueError(f"Unsupported bibliography format: {fmt}")


def _markdown_references(records: list[CitationRecord]) -> str:
    lines = ["# References", ""]
    for index, record in enumerate(records, start=1):
        authors = ", ".join(record.authors) if record.authors else "Unknown"
        year = record.year or "n.d."
        pub = f" *{record.publication}*" if record.publication else ""
        doi = f" https://doi.org/{record.doi}" if record.doi else ""
        lines.append(f"{index}. {authors} ({year}). **{record.title}**.{pub}{doi}")
    return "\n".join(lines) + "\n"


def _report_section(records: list[CitationRecord]) -> str:
    body = _markdown_references(records)
    return "## Bibliography\n\n" + body.removeprefix("# References\n\n")

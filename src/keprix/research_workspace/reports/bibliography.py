"""Bibliography helpers for report rendering (wraps citations module)."""

from __future__ import annotations

from keprix.research_workspace.citations.bibliography import export_bibliography
from keprix.research_workspace.citations.models import CitationRecord

__all__ = ["export_bibliography", "CitationRecord", "render_report_bibliography"]


def render_report_bibliography(records: list[CitationRecord]) -> str:
    """Return the bibliography section used in assembled reports."""
    if not records:
        return "## Bibliography\n\n_No citations registered for this project._\n"
    return export_bibliography(records, "report")

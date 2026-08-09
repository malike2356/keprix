"""Guards for the spreadsheet-style outreach lead tracker."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_outreach_leads_exposes_source_provenance_table() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/outreach/leads/page.tsx").read_text(encoding="utf-8")
    for marker in (
        'aria-label="Outreach lead tracker"',
        "All sources",
        "Source page",
        "Companies House",
        "Internet research",
        "listing_page",
        "lead.source_url",
        "safeSourceUrl",
    ):
        assert marker in page


def test_outreach_create_route_preserves_source_url() -> None:
    route = (ROOT / "src/keprix/outreach/ui_routes.py").read_text(encoding="utf-8")
    assert '"source_url": body.get("source_url")' in route

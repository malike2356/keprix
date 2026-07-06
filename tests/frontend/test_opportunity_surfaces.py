"""Prompt 94 guards for Opportunity UI and API client."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/lib/opportunity-api.ts",
    "frontend/src/app/(workspace)/opportunities/page.tsx",
    "frontend/src/app/(workspace)/opportunities/[id]/page.tsx",
    "frontend/src/components/opportunity/OpportunityCreatePanel.tsx",
    "frontend/src/components/opportunity/OpportunityTimeline.tsx",
    "frontend/src/components/opportunity/OpportunityArtifactViewer.tsx",
    "frontend/src/components/opportunity/OpportunityScoreCard.tsx",
    "frontend/src/components/opportunity/OpportunityApprovalQueue.tsx",
    "frontend/src/components/opportunity/OpportunityIntegrationStatus.tsx",
    "src/keprix/opportunity/slash.py",
]


def test_opportunity_surface_files_exist():
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_opportunity_api_client_exports():
    source = (ROOT / "frontend/src/lib/opportunity-api.ts").read_text(encoding="utf-8")
    for name in (
        "createOpportunity",
        "listOpportunities",
        "fetchOpportunity",
        "runOpportunityPipeline",
        "runOpportunityPhase",
        "fetchOpportunityArtifact",
        "approveOpportunityAction",
        "pauseOpportunity",
        "archiveOpportunity",
    ):
        assert f"export async function {name}" in source


def test_opportunity_ui_uses_playbook_terminology():
    detail = (ROOT / "frontend/src/app/(workspace)/opportunities/[id]/page.tsx").read_text(encoding="utf-8")
    assert "playbook" in detail.lower()
    assert "recipe" not in detail.lower()


def test_navigation_includes_opportunities():
    nav = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert 'href: "/opportunities"' in nav

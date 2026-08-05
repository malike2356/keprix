"""Frontend guards for unified /data workspace tabs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_data_workspace_page_hosts_panels() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/data/page.tsx").read_text(encoding="utf-8")
    client = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(encoding="utf-8")
    assert "DataWorkspaceClient" in page
    assert "DataSectionTabs" in client
    assert "parseDataTab" in client
    assert "AnalyticsPanel" in client
    assert "VideoIngestPanel" in client
    assert "UsagePanel" in client
    assert "dataHref(next)" in client


def test_legacy_data_routes_redirect_to_data_tabs() -> None:
    mapping = {
        "rag-pipeline/page.tsx": "rag",
        "playbook/page.tsx": "models",
        "ingest/video/page.tsx": "video",
        "analytics/page.tsx": "analytics",
        "usage/page.tsx": "usage",
        "observability/page.tsx": "observability",
    }
    for rel, tab in mapping.items():
        text = (ROOT / "frontend/src/app/(workspace)" / rel).read_text(encoding="utf-8")
        assert "redirect(" in text
        assert f'tab", "{tab}"' in text or f"tab\", \"{tab}\"" in text


def test_nav_points_data_group_at_data_tabs() -> None:
    nav = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert 'href: "/data?tab=rag"' in nav
    assert 'href: "/data?tab=models"' in nav
    assert 'href: "/data?tab=video"' in nav
    assert 'href: "/data?tab=analytics"' in nav
    assert 'href: "/data?tab=usage"' in nav
    assert 'href: "/data?tab=observability"' in nav


def test_analytics_panel_keeps_must_haves() -> None:
    panel = (ROOT / "frontend/src/components/data/panels/AnalyticsPanel.tsx").read_text(encoding="utf-8")
    assert "Dataset library" in panel
    assert "renameAnalyticsSession" in panel
    assert "Run history" in panel
    assert "DataSectionTabs" not in panel

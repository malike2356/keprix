"""Frontend guards for data-ops P0 usage + observability surfaces."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_usage_page_wires_export_and_filters() -> None:
    page = (ROOT / "frontend/src/components/data/panels/UsagePanel.tsx").read_text(encoding="utf-8")
    data_page = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(encoding="utf-8")
    assert "downloadUsageExport" in page
    assert "Export CSV" in page
    assert "Export JSON" in page
    assert "Channel / agent" in page
    assert "fetchUsageStatus" in page
    assert "DataSectionTabs" in data_page
    assert "UsagePanel" in data_page


def test_observability_page_is_runtime_health() -> None:
    page = (ROOT / "frontend/src/components/data/panels/ObservabilityPanel.tsx").read_text(encoding="utf-8")
    data_page = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(encoding="utf-8")
    assert "Runtime health" in page
    assert "Span timeline" in page
    assert "exportObservabilityTrace" in page
    assert "Live refresh" in page or "refresh interval" in page.lower()
    assert "ObservabilityPanel" in data_page
    assert "/data?tab=usage" in page


def test_nav_icons_distinct_for_usage_and_observability() -> None:
    nav = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    icons = (ROOT / "frontend/src/lib/nav-icons.ts").read_text(encoding="utf-8")
    assert 'id: "usage"' in nav and 'icon: "monitoring"' in nav
    assert 'id: "observability"' in nav and 'icon: "activity"' in nav
    assert 'href: "/data?tab=usage"' in nav
    assert 'href: "/data?tab=observability"' in nav
    assert "activity: IconActivity" in icons
    contract = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    assert '"icon": "activity"' in contract


def test_settings_canonical_usage_link() -> None:
    settings = (ROOT / "frontend/src/app/(workspace)/settings/page.tsx").read_text(encoding="utf-8")
    assert settings.count('href: "/data?tab=usage"') == 1
    assert 'href: "/dashboard/usage"' not in settings or settings.count("LLM usage and budgets") == 0

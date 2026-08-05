"""Frontend guards for data-ops P4 analytics Must surface."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_analytics_page_has_data_tabs_and_titles() -> None:
    panel = (ROOT / "frontend/src/components/data/panels/AnalyticsPanel.tsx").read_text(encoding="utf-8")
    assert "Session title" in panel
    assert "renameAnalyticsSession" in panel
    assert "Dataset library" in panel
    assert "saveAnalyticsDataset" in panel
    assert "deleteAnalyticsDataset" in panel
    assert "Run history" in panel
    assert "Re-run #" in panel
    assert "export:" in panel or "png:" in panel
    assert "No chart points" in panel
    data_page = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(encoding="utf-8")
    assert "DataSectionTabs" in data_page
    assert "AnalyticsPanel" in data_page


def test_analytics_api_has_dataset_and_csv_helpers() -> None:
    api = (ROOT / "frontend/src/lib/analytics-api.ts").read_text(encoding="utf-8")
    assert "renameAnalyticsSession" in api
    assert "/api/analytics/datasets" in api
    assert "parseCsvRows" in api
    assert "quoted commas" in api.lower() or "RFC4180" in api

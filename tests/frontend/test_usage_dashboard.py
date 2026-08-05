"""Prompt 147 guards for LLM usage workspace dashboard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/lib/usage-api.ts",
    "frontend/src/lib/usage-format.ts",
    "frontend/src/app/(workspace)/usage/page.tsx",
    "frontend/src/components/usage/UsageStatCard.tsx",
    "frontend/src/components/usage/UsagePeriodToolbar.tsx",
    "frontend/src/components/usage/UsageTimeseriesChart.tsx",
    "frontend/src/components/usage/UsageModelBreakdownChart.tsx",
    "frontend/src/components/usage/UsageRecentTable.tsx",
    "frontend/src/components/usage/UsageBudgetBanner.tsx",
]


def test_usage_dashboard_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_usage_api_client_exports() -> None:
    source = (ROOT / "frontend/src/lib/usage-api.ts").read_text(encoding="utf-8")
    for name in (
        "fetchUsageSummary",
        "fetchUsageTimeseries",
        "fetchUsageBreakdown",
        "fetchUsageBudget",
        "fetchUsageEvents",
    ):
        assert f"export async function {name}" in source


def test_usage_page_renders_stat_card_labels() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/usage/page.tsx").read_text(encoding="utf-8")
    for label in (
        "Total tokens",
        "Estimated cost (USD)",
        "API calls",
        "Avg cost per call",
    ):
        assert label in page


def test_usage_page_uses_summary_values() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/usage/page.tsx").read_text(encoding="utf-8")
    assert "fetchUsageSummary" in page
    assert "summary?.total_tokens" in page
    assert "summary?.total_cost_usd" in page
    assert "summary?.request_count" in page
    assert "summary?.avg_cost_per_request_usd" in page


def test_usage_period_toolbar_changes_swr_keys() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/usage/page.tsx").read_text(encoding="utf-8")
    assert "usage-summary" in page
    assert "UsagePeriodToolbar" in page
    assert "periodDays" in page
    toolbar = (ROOT / "frontend/src/components/usage/UsagePeriodToolbar.tsx").read_text(encoding="utf-8")
    assert "storeUsagePeriod" in toolbar


def test_usage_empty_state_when_no_requests() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/usage/page.tsx").read_text(encoding="utf-8")
    assert "No LLM usage recorded yet" in page
    assert "request_count" in page
    assert 'href="/chat"' in page


def test_navigation_includes_usage() -> None:
    nav = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert 'href: "/usage"' in nav
    contract = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    assert '"/usage"' in contract


def test_recent_table_links_chat_sessions() -> None:
    table = (ROOT / "frontend/src/components/usage/UsageRecentTable.tsx").read_text(encoding="utf-8")
    assert "/chat/${row.session_id}" in table or "`/chat/${row.session_id}`" in table

"""Prompt 148 guards for admin LLM usage dashboard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/app/(admin)/dashboard/usage/page.tsx",
    "frontend/src/components/admin/usage/UsageBudgetPanel.tsx",
    "frontend/src/components/admin/usage/UsageChannelBreakdownChart.tsx",
    "frontend/src/components/admin/usage/UsageUserBreakdownTable.tsx",
    "frontend/src/components/admin/usage/UsageModelBreakdownTable.tsx",
    "frontend/src/components/admin/usage/UsageAdminEventLog.tsx",
    "src/keprix/usage/budget_alerts.py",
    "src/keprix/api/stats_routes.py",
]


def test_admin_usage_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_admin_usage_page_renders_budget_form() -> None:
    page = (ROOT / "frontend/src/app/(admin)/dashboard/usage/page.tsx").read_text(encoding="utf-8")
    assert "UsageBudgetPanel" in page
    assert "updateUsageBudget" in page
    budget = (ROOT / "frontend/src/components/admin/usage/UsageBudgetPanel.tsx").read_text(encoding="utf-8")
    assert "Monthly budget (USD)" in budget
    assert "Save budget" in budget


def test_admin_usage_export_button() -> None:
    event_log = (ROOT / "frontend/src/components/admin/usage/UsageAdminEventLog.tsx").read_text(encoding="utf-8")
    page = (ROOT / "frontend/src/app/(admin)/dashboard/usage/page.tsx").read_text(encoding="utf-8")
    assert "Export CSV" in event_log
    assert "downloadUsageExport" in page


def test_admin_usage_user_breakdown_headers() -> None:
    table = (ROOT / "frontend/src/components/admin/usage/UsageUserBreakdownTable.tsx").read_text(encoding="utf-8")
    for header in ("User", "Requests", "Tokens", "Cost", "Share"):
        assert header in table


def test_admin_nav_includes_usage() -> None:
    nav = (ROOT / "frontend/src/components/admin/admin-nav.ts").read_text(encoding="utf-8")
    assert 'href: "/dashboard/usage"' in nav


def test_admin_dashboard_links_llm_spend() -> None:
    page = (ROOT / "frontend/src/app/(admin)/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "LLM spend (30d)" in page
    assert 'href="/dashboard/usage"' in page
    api = (ROOT / "frontend/src/lib/admin-dashboard-api.ts").read_text(encoding="utf-8")
    assert "llmSpend30d" in api

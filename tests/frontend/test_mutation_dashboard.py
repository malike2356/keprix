"""Prompt 155 guards for mutation governance UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/lib/mutation-api.ts",
    "frontend/src/app/(admin)/dashboard/mutation/page.tsx",
    "frontend/src/app/(admin)/dashboard/mutation/[id]/page.tsx",
    "frontend/src/components/mutation/MutationApprovalPanel.tsx",
    "frontend/src/components/mutation/MutationQualityBadge.tsx",
    "frontend/src/components/mutation/GeneratedToolCard.tsx",
    "frontend/src/components/mutation/DiffViewer.tsx",
    "frontend/src/components/mutation/MutationHistoryTable.tsx",
    "frontend/src/components/mutation/CompoundingMetricsCard.tsx",
    "src/keprix/mutation/routes.py",
]


def test_mutation_governance_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_mutation_page_has_five_tabs() -> None:
    page = (ROOT / "frontend/src/app/(admin)/dashboard/mutation/page.tsx").read_text(encoding="utf-8")
    for tab in ("pending", "tools", "prompts", "code", "history"):
        assert tab in page
    assert "Pending (" in page


def test_approve_button_calls_api() -> None:
    panel = (ROOT / "frontend/src/components/mutation/MutationApprovalPanel.tsx").read_text(encoding="utf-8")
    assert "approveMutation" in panel
    assert "/approve" not in panel


def test_diff_viewer_renders_added_lines_green() -> None:
    diff = (ROOT / "frontend/src/components/mutation/DiffViewer.tsx").read_text(encoding="utf-8")
    assert "success.light" in diff
    assert "error.light" in diff
    assert 'type === "add"' in diff


def test_code_tab_merge_confirmation_modal() -> None:
    page = (ROOT / "frontend/src/app/(admin)/dashboard/mutation/page.tsx").read_text(encoding="utf-8")
    assert "Merge mutation branch into main?" in page
    assert "Merge and Approve" in page


def test_quality_badge_color_thresholds() -> None:
    badge = (ROOT / "frontend/src/components/mutation/MutationQualityBadge.tsx").read_text(encoding="utf-8")
    assert "0.75" in badge
    assert "0.45" in badge
    assert 'score === null' in badge


def test_history_tab_filters_by_tier() -> None:
    table = (ROOT / "frontend/src/components/mutation/MutationHistoryTable.tsx").read_text(encoding="utf-8")
    assert 'value="tool"' in table
    assert "onFiltersChange" in table


def test_compounding_metrics_card_renders_divergence() -> None:
    card = (ROOT / "frontend/src/components/mutation/CompoundingMetricsCard.tsx").read_text(encoding="utf-8")
    assert "divergence_score" in card
    assert "CircularProgress" in card


def test_admin_overview_pending_alert_banner() -> None:
    page = (ROOT / "frontend/src/app/(admin)/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "awaiting approval" in page
    assert "CompoundingMetricsCard" in page
    assert 'href="/dashboard/mutation"' in page


def test_admin_nav_mutation_route_and_badge() -> None:
    nav = (ROOT / "frontend/src/components/admin/admin-nav.ts").read_text(encoding="utf-8")
    assert 'href: "/dashboard/mutation"' in nav
    assert "badgeKey: \"pendingMutations\"" in nav
    sidebar = (ROOT / "frontend/src/components/admin/Sidebar.tsx").read_text(encoding="utf-8")
    assert "fetchMutationStats" in sidebar
    assert "refreshInterval: 30_000" in sidebar


def test_mutation_api_hooks() -> None:
    api = (ROOT / "frontend/src/lib/mutation-api.ts").read_text(encoding="utf-8")
    for symbol in (
        "useMutationQueue",
        "useGeneratedTools",
        "usePromptVersions",
        "useCodeMutations",
        "useMutationHistory",
        "useMutationDetail",
        "useQualityHistory",
        "useCompoundingMetrics",
        "triggerPrune",
    ):
        assert symbol in api


def test_mutation_detail_page_quality_history() -> None:
    page = (ROOT / "frontend/src/app/(admin)/dashboard/mutation/[id]/page.tsx").read_text(encoding="utf-8")
    assert "useQualityHistory" in page
    assert "Quality history" in page

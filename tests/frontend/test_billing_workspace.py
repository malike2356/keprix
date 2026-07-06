"""Prompt 156 guards for workspace billing UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/lib/billing-api.ts",
    "frontend/src/lib/billing-format.ts",
    "frontend/src/app/(workspace)/settings/billing/page.tsx",
    "frontend/src/components/billing/BillingPlanCard.tsx",
    "frontend/src/components/billing/BillingPlanCompare.tsx",
    "frontend/src/components/billing/BillingSubscriptionSummary.tsx",
    "frontend/src/components/billing/BillingInvoiceTable.tsx",
    "frontend/src/components/billing/BillingSeatsPanel.tsx",
    "frontend/src/components/billing/BillingDisabledState.tsx",
    "frontend/src/components/billing/BillingCheckoutBanner.tsx",
]


def test_billing_workspace_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_billing_api_client_exports() -> None:
    source = (ROOT / "frontend/src/lib/billing-api.ts").read_text(encoding="utf-8")
    for name in (
        "fetchBillingStatus",
        "fetchBillingAccount",
        "fetchBillingInvoices",
        "startCheckout",
        "startTrial",
        "cancelSubscription",
        "resumeSubscription",
        "openPaymentMethodPortal",
        "isBillingGateError",
    ):
        assert f"export async function {name}" in source or f"export function {name}" in source


def test_billing_page_disabled_copy() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/settings/billing/page.tsx").read_text(encoding="utf-8")
    assert "BillingDisabledState" in page
    assert "SaaS billing is not enabled" in (
        ROOT / "frontend/src/components/billing/BillingDisabledState.tsx"
    ).read_text(encoding="utf-8")


def test_billing_plan_card_labels_and_checkout() -> None:
    card = (ROOT / "frontend/src/components/billing/BillingPlanCard.tsx").read_text(encoding="utf-8")
    for label in ("Subscribe", "Start trial", "Current plan", "Upgrade"):
        assert label in card
    page = (ROOT / "frontend/src/components/billing/BillingSettingsContent.tsx").read_text(encoding="utf-8")
    assert "redirectToCheckout" in page
    assert "checkoutBanner" in page


def test_navigation_includes_billing() -> None:
    nav = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert 'href: "/settings/billing"' in nav
    contract = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    assert '"/settings/billing"' in contract


def test_settings_hub_links_billing() -> None:
    settings = (ROOT / "frontend/src/app/(workspace)/settings/page.tsx").read_text(encoding="utf-8")
    assert "Billing and subscription" in settings
    assert 'href: "/settings/billing"' in settings

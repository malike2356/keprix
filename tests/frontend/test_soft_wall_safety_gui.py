"""Frontend + API guards for Soft Wall safety GUIs (prompts 469-474)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


SAFETY_PAGES = {
    "deliverability": "fetchCrmDeliverability",
    "outbox": "fetchCrmOutbox",
    "suppressions": "fetchCrmSuppressions",
    "contactability": "fetchCrmContactability",
    "merges": "fetchCrmMerges",
    "settings": "fetchCrmKillSwitches",
}


def test_soft_wall_safety_pages_exist() -> None:
    for slug, api_symbol in SAFETY_PAGES.items():
        page = (
            ROOT / f"frontend/src/app/(workspace)/outreach/{slug}/page.tsx"
        ).read_text(encoding="utf-8")
        assert api_symbol in page or "crm-api" in page
        assert "EmptyState" in page or "empty" in page.lower()


def test_outreach_tab_nav_includes_safety_tabs() -> None:
    nav = (
        ROOT / "frontend/src/components/outreach/OutreachTabNav.tsx"
    ).read_text(encoding="utf-8")
    for href in (
        "/outreach/deliverability",
        "/outreach/outbox",
        "/outreach/suppressions",
        "/outreach/contactability",
        "/outreach/merges",
        "/outreach/settings",
    ):
        assert href in nav


def test_crm_api_client_covers_safety_endpoints() -> None:
    api = (ROOT / "frontend/src/lib/crm-api.ts").read_text(encoding="utf-8")
    for path in (
        "/api/crm/deliverability",
        "/api/crm/outbox",
        "/api/crm/outbox/",
        "/api/crm/suppressions",
        "/api/crm/suppressions/bulk",
        "/api/crm/contactability",
        "/api/crm/merges",
        "/api/crm/kill-switches",
    ):
        assert path in api


def test_deliverability_helper_honest_zeros() -> None:
    from keprix.crm.deliverability import compute_deliverability_snapshot
    from keprix.crm.store import CrmStore
    import tempfile

    store = CrmStore(Path(tempfile.mkdtemp()) / "t.db")
    snap = compute_deliverability_snapshot(store, "ws")
    assert snap["rates"]["bounce_rate_pct"] == 0.0
    assert snap["rates"]["complaint_rate_pct"] == 0.0
    assert snap["soft_wall_block_cold_send"] is True
    assert "demo" not in str(snap).lower()


def test_outbox_retry_keeps_idempotency_key() -> None:
    from keprix.crm.models import OutboxStatus
    from keprix.crm.store import CrmStore
    import tempfile

    store = CrmStore(Path(tempfile.mkdtemp()) / "o.db")
    row = store.enqueue_outbox(
        "ws",
        kind="email_send",
        idempotency_key="idem-1",
        payload={"to": "a@b.c"},
        status=OutboxStatus.DEAD_LETTER,
    )
    assert row["idempotency_key"] == "idem-1"
    updated = store.update_outbox("ws", row["id"], status=OutboxStatus.PENDING, last_error=None)
    assert updated is not None
    assert updated["idempotency_key"] == "idem-1"
    again = store.enqueue_outbox(
        "ws",
        kind="email_send",
        idempotency_key="idem-1",
        payload={"to": "a@b.c"},
    )
    assert again["id"] == row["id"]

"""Frontend smoke for discovery GUI + CRM Must routes (466 / 479-481 / 450)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CRM_MUST_ROUTES = [
    "page.tsx",
    "accounts/page.tsx",
    "accounts/[id]/page.tsx",
    "leads/page.tsx",
    "leads/[id]/page.tsx",
    "contacts/page.tsx",
    "contacts/[id]/page.tsx",
    "deals/page.tsx",
    "deals/[id]/page.tsx",
    "lists/page.tsx",
    "lists/[id]/page.tsx",
    "discover/page.tsx",
    "jobs/page.tsx",
    "enrich/page.tsx",
    "inbox/page.tsx",
    "workflows/page.tsx",
    "deliverability/page.tsx",
    "outbox/page.tsx",
    "merges/page.tsx",
    "contactability/page.tsx",
    "suppressions/page.tsx",
    "settings/page.tsx",
]

# Soft Wall-gated Must surfaces must expose operator actions in GUI copy/API.
SOFT_WALL_ACTION_MARKERS: dict[str, tuple[str, ...]] = {
    "lists/[id]/page.tsx": ("enrollCrmList", "preflightCrmListEnroll", "CrmSoftWallPanel"),
    "enrich/page.tsx": ("applyCrmSheetJob", "proposeCrmSheet"),
    "jobs/page.tsx": ("fetchCrmJobs",),
    "inbox/page.tsx": ("claimCrmInboxItem", "pauseCrmInboxItem"),
    "outbox/page.tsx": ("retryCrmOutbox",),
    "merges/page.tsx": ("applyCrmMerge", "rejectCrmMerge", "Soft Wall"),
    "contactability/page.tsx": ("upsertCrmContactability",),
    "settings/page.tsx": ("upsertCrmKillSwitch", "Soft Wall"),
    "deliverability/page.tsx": ("fetchCrmDeliverability",),
    "workflows/page.tsx": ("setCrmWorkflowStatus", "Soft Wall"),
    "page.tsx": ("CrmSoftWallPanel", "fetchCrmKillSwitches"),
}


def test_discovery_pages_and_api_client() -> None:
    discover = (ROOT / "frontend/src/app/(workspace)/crm/discover/page.tsx").read_text(
        encoding="utf-8"
    )
    jobs = (ROOT / "frontend/src/app/(workspace)/crm/jobs/page.tsx").read_text(encoding="utf-8")
    assert "runDiscoveryJob" in discover or "fetchDiscoveryAdapters" in discover
    assert "fetchCrmJobs" in jobs
    assert "companies_house" in discover
    api = (ROOT / "frontend/src/lib/crm-api.ts").read_text(encoding="utf-8")
    assert "/api/crm/discovery" in api or "discovery/adapters" in api or "runDiscoveryJob" in api


def test_discovery_nav_entries() -> None:
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    ts = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert "/crm/discover" in py and "/crm/jobs" in py
    assert "/crm/discover" in ts and "/crm/jobs" in ts
    tabs = (ROOT / "frontend/src/components/crm/CrmTabNav.tsx").read_text(encoding="utf-8")
    assert "/crm/discover" in tabs and "/crm/deliverability" in tabs and "/crm/outbox" in tabs


def test_crm_funnel_flag_gates_all_crm_nav_ids() -> None:
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    assert '"crm_funnel"' in py or "'crm_funnel'" in py
    # When flag off, hide overview + enrich + discover + jobs (not only overview).
    gate_line = [ln for ln in py.splitlines() if "crm_funnel" in ln and "FLAG" not in ln]
    assert gate_line, "crm_funnel FLAG_NAV_GATES entry missing"
    joined = " ".join(gate_line)
    for nav_id in ("crm", "crm-enrich", "crm-discover", "crm-jobs"):
        assert nav_id in joined, f"crm_funnel should gate {nav_id}"


def test_crm_must_routes_exist_not_stubs() -> None:
    base = ROOT / "frontend/src/app/(workspace)/crm"
    for rel in CRM_MUST_ROUTES:
        path = base / rel
        assert path.is_file(), f"missing {rel}"
        text = path.read_text(encoding="utf-8")
        assert "CrmStubPage" not in text, f"{rel} still stub"
        assert "(later)" not in text.lower() or "Nice" in text, f"{rel} still says later"


def test_crm_soft_wall_actions_surfaced() -> None:
    base = ROOT / "frontend/src/app/(workspace)/crm"
    for rel, markers in SOFT_WALL_ACTION_MARKERS.items():
        text = (base / rel).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text, f"{rel} missing Soft Wall/GUI marker {marker}"


def test_crm_tab_nav_covers_ia_table() -> None:
    tabs = (ROOT / "frontend/src/components/crm/CrmTabNav.tsx").read_text(encoding="utf-8")
    for href in (
        "/crm",
        "/crm/accounts",
        "/crm/leads",
        "/crm/contacts",
        "/crm/deals",
        "/crm/lists",
        "/crm/discover",
        "/crm/jobs",
        "/crm/enrich",
        "/crm/inbox",
        "/crm/workflows",
        "/crm/deliverability",
        "/crm/outbox",
        "/crm/merges",
        "/crm/contactability",
        "/crm/suppressions",
        "/crm/settings",
    ):
        assert href in tabs, f"CrmTabNav missing {href}"


def test_docs_sitemap_matches_ia() -> None:
    feature = (ROOT / "docs/features/agentic-crm.md").read_text(encoding="utf-8")
    for href in (
        "/crm/jobs",
        "/crm/inbox",
        "/crm/deliverability",
        "/crm/outbox",
        "/crm/merges",
        "/crm/contactability",
        "/crm/settings",
        "/crm/workflows",
    ):
        assert href in feature, f"agentic-crm.md missing {href}"


def test_discovery_package_mounted() -> None:
    server = (ROOT / "src/keprix/api/server.py").read_text(encoding="utf-8")
    assert "crm_discovery_router" in server or "discovery.routes" in server
    assert (ROOT / "src/keprix/discovery/adapters/fake.py").is_file()
    assert (ROOT / "src/keprix/discovery/adapters/companies_house.py").is_file()
    assert (ROOT / "src/keprix/discovery/packs/generic.yaml").is_file()

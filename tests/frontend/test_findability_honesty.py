"""Findability + honesty smoke for prompts 497-504."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_nav_orphans_and_commerce() -> None:
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    ts = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert "/document-agents" in py and "/document-agents" in ts
    assert 'group": "commerce"' in py or "group\": \"commerce\"" in py
    assert 'group: "commerce"' in ts
    assert "/admin/workspace-ops" in py and "/admin/workspace-ops" in ts
    assert (ROOT / "frontend/src/app/(workspace)/document-agents/page.tsx").is_file()
    assert (ROOT / "frontend/src/app/(workspace)/admin/workspace-ops/page.tsx").is_file()


def test_leads_and_opportunities_clarity() -> None:
    leads = (ROOT / "frontend/src/app/(workspace)/leads/page.tsx").read_text(encoding="utf-8")
    opp = (ROOT / "frontend/src/app/(workspace)/opportunities/page.tsx").read_text(encoding="utf-8")
    assert "Product signups" in leads
    assert "/api/leads" in leads or "fetchLeads" in leads
    assert "Research opportunities" in opp
    assert "/crm/deals" in opp
    glossary = (ROOT / "docs/features/leads-opportunities-glossary.md").read_text(encoding="utf-8")
    assert "/crm/leads" in glossary


def test_gui_catalog_honesty() -> None:
    from keprix.upgrade.gui_catalog import modules_payload

    payload = modules_payload()
    by_id = {m["id"]: m for m in payload["modules"]}
    for key in ("tool_acl", "fleet_admin", "companion_pairing", "data_plane_datasets", "jobs_queue"):
        assert by_id[key]["gui_status"] == "available"
        assert by_id[key]["gui_href"]
    assert by_id["public_v1_api"]["gui_status"] == "integration"
    assert "missing_gui" in payload["counts"]


def test_proxy_ops_and_intentional_register() -> None:
    assert (ROOT / "src/keprix/proxy/http_routes.py").is_file()
    cred = (ROOT / "frontend/src/app/(admin)/dashboard/credentials/page.tsx").read_text(
        encoding="utf-8"
    )
    assert "ProxyOpsPanel" in cred
    inv = (ROOT / "docs/architecture/operator-gui-gap-inventory.md").read_text(encoding="utf-8")
    assert "Intentional non-GUI register" in inv

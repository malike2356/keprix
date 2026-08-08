"""Saved versioned ICP definitions (prompt 452)."""

from __future__ import annotations

from pathlib import Path


def test_icp_version_activate_and_diff(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    from keprix.crm import icp as icp_mod
    from keprix.crm.store import CrmStore

    store = CrmStore(tmp_path / "crm.db")
    ws = "ws_icp"
    v1 = icp_mod.create_icp(
        store,
        ws,
        name="Plumbers NW",
        pack="plumbing",
        include_rules=[{"field": "keyword", "value": "plumb"}],
        exclude_rules=[{"field": "domain", "value": "spam.test"}],
        notes="v1",
    )
    assert v1["version"] == 1
    assert v1["active"] is False

    blocked = icp_mod.activate_icp(store, ws, v1["id"])
    assert blocked.get("blocked") is True

    activated = icp_mod.activate_icp(store, ws, v1["id"], force=True)
    assert activated["ok"] is True
    assert activated["icp"]["active"] is True

    v2 = icp_mod.revise_icp(
        store,
        ws,
        v1["id"],
        exclude_rules=[
            {"field": "domain", "value": "spam.test"},
            {"field": "keyword", "value": "agency"},
        ],
        notes="v2",
    )
    assert v2["version"] == 2
    assert v2["active"] is False
    # v1 remains active until Soft Wall switches
    assert icp_mod.get_icp(store, ws, v1["id"])["active"] is True

    diff = icp_mod.diff_icp_versions(v1, v2)
    assert diff["changed"] is True
    fields = {c["field"] for c in diff["changes"]}
    assert "exclude_rules" in fields
    assert "notes" in fields

    switched = icp_mod.activate_icp(store, ws, v2["id"], force=True)
    assert switched["ok"] is True
    assert icp_mod.get_icp(store, ws, v1["id"])["active"] is False
    assert icp_mod.get_active_icp(store, ws)["id"] == v2["id"]


def test_icp_exclusions_and_discovery_tag(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    monkeypatch.setenv("KEPRIX_DISCOVERY_SOFT_WALL_MATERIALIZE", "0")
    from keprix.crm import icp as icp_mod
    from keprix.crm.store import CrmStore
    from keprix.discovery.materialize import materialize_candidates
    from keprix.discovery.models import LeadCandidate

    store = CrmStore(tmp_path / "crm2.db")
    ws = "ws_icp2"
    icp = icp_mod.create_icp(
        store,
        ws,
        name="Exclude agencies",
        exclude_rules=[{"field": "keyword", "value": "agency"}],
    )
    icp_mod.activate_icp(store, ws, icp["id"], force=True)

    kept = {
        "name": "Good Plumb Ltd",
        "company_name": "Good Plumb Ltd",
        "domain": "goodplumb.example",
        "emails": [{"address": "a@goodplumb.example"}],
    }
    drop = {
        "name": "Marketing Agency",
        "company_name": "Marketing Agency",
        "domain": "agency.example",
        "emails": [{"address": "b@agency.example"}],
    }
    filt = icp_mod.apply_icp_exclusions(store, ws, [kept, drop])
    assert len(filt["kept"]) == 1
    assert len(filt["excluded"]) == 1
    assert filt["excluded"][0]["reason"] == "icp_exclude"

    result = materialize_candidates(
        ws,
        [
            LeadCandidate(company="Good Plumb Ltd", emails=["a@goodplumb.example"], domain="goodplumb.example"),
            LeadCandidate(company="Marketing Agency", emails=["b@agency.example"], domain="agency.example"),
        ],
        list_name="ICP test list",
        store=store,
        skip_soft_wall=True,
        icp_id=icp["id"],
        icp_version=1,
    )
    assert result["blocked"] is False
    assert result["member_count"] == 1
    assert len(result["icp_excluded"]) == 1
    lst = store.get_list(ws, result["list_id"])
    assert lst.get("icp_id") == icp["id"]
    assert int(lst.get("icp_version") or 0) == 1

    job = store.create_discovery_job(ws, "fake", params={"query": "x"}, domain_pack="generic")
    icp_mod.stamp_entity_icp(
        store, ws, entity_type="discovery_job", entity_id=job["id"], icp_id=icp["id"], icp_version=1
    )
    tagged = store.get_discovery_job(ws, job["id"])
    assert tagged.get("icp_id") == icp["id"]
    assert int(tagged.get("icp_version") or 0) == 1


def test_icp_tools_registered() -> None:
    import keprix.tools.crm_tools  # noqa: F401
    from tools.registry import registry

    assert registry.get_entry("crm_icp_list") is not None
    assert registry.get_entry("crm_icp_use") is not None

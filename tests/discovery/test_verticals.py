"""Web directory + social + property + health pack tests (438-441)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.crm.soft_wall import gate_or_approve
from keprix.crm.store import reset_crm_store_for_tests
from keprix.discovery import (
    DiscoverLimits,
    DiscoverQuery,
    get_discovery_registry,
    reset_discovery_registry_for_tests,
)
from keprix.discovery.adapters.health import CqcApiAdapter, HealthCsvAdapter
from keprix.discovery.adapters.property_portals import (
    PROPERTY_PORTAL_FLAG,
    RightmoveHttpAdapter,
    ZooplaHttpAdapter,
)
from keprix.discovery.adapters.social import LinkedInApiAdapter, scrape_refusal_payload
from keprix.discovery.adapters.web_directory import WebDirectoryAdapter
from keprix.discovery.materialize import enroll_requires_soft_wall
from keprix.discovery.packs import get_pack, load_vertical_packs
from keprix.outreach.ops import OutreachOpsStore
from keprix.outreach.store import reset_outreach_store_for_tests
from keprix.sheet_preprocess.registry import get_sheet_type_registry


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    reset_discovery_registry_for_tests()
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_web_directory_mocked_results_no_fetch_by_default():
    adapter = WebDirectoryAdapter()
    cands = adapter.discover(
        DiscoverQuery(
            text="plumbers",
            domain_pack="plumbing",
            params={
                "location": "Manchester",
                "search_results": [
                    {
                        "title": "Manchester Plumbers Ltd",
                        "url": "https://example-plumbers.test",
                        "snippet": "Local plumbers",
                    }
                ],
            },
        ),
        DiscoverLimits(max_results=10, allow_homepage_fetch=False, max_fetches=5),
    )
    assert len(cands) == 1
    assert cands[0].source == "web_directory"
    assert "homepage_fetch" not in (cands[0].raw or {})


def test_web_directory_egress_denied_on_fetch(monkeypatch):
    adapter = WebDirectoryAdapter()
    from keprix.security.egress_policy import EgressDecision, get_egress_policy

    policy = get_egress_policy()
    policy.load_product("keprix", allowed_hosts=set(), default_deny=True)

    cands = adapter.discover(
        DiscoverQuery(
            params={
                "search_results": [
                    {"title": "Blocked Co", "url": "https://not-allowed.example", "snippet": "x"}
                ],
                "approve_homepage_fetch": True,
            }
        ),
        DiscoverLimits(allow_homepage_fetch=True, max_fetches=1, max_results=5),
    )
    assert cands[0].raw.get("homepage_fetch", {}).get("error") == "egress_denied"


def test_social_unconfigured_and_configured_mapping(monkeypatch):
    monkeypatch.delenv("LINKEDIN_CLIENT_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    adapter = LinkedInApiAdapter()
    health = adapter.health()
    assert health.status.value == "not_configured"
    with pytest.raises(RuntimeError, match="not configured|credentials missing|Set "):
        adapter.discover(DiscoverQuery(text="x"), DiscoverLimits())

    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret")
    cands = adapter.discover(
        DiscoverQuery(
            params={
                "api_payload": [
                    {"id": "pg1", "name": "Org Page", "email": "leads@org.example", "url": "https://li.example/pg1"}
                ]
            }
        ),
        DiscoverLimits(max_results=5),
    )
    assert len(cands) == 1
    assert cands[0].company == "Org Page"
    assert cands[0].source == "linkedin_api"

    refusal = scrape_refusal_payload("instagram_scrape")
    assert refusal["refused"] is True
    assert "API" in refusal["message"] or "api" in refusal["message"].lower()


def test_property_pack_and_portal_disabled(monkeypatch):
    monkeypatch.delenv(PROPERTY_PORTAL_FLAG, raising=False)
    packs = load_vertical_packs(force=True)
    assert "property" in packs
    prop = get_pack("property")
    assert prop is not None
    sheet_ids = {st["id"] for st in prop["sheet_types"]}
    assert {"property_data", "tenant_list", "landlord_pipeline"} <= sheet_ids
    registry = get_sheet_type_registry()
    assert "landlord_pipeline" in registry.known_types()

    rightmove = RightmoveHttpAdapter()
    assert rightmove.health().status.value == "disabled"
    with pytest.raises(RuntimeError, match="disabled"):
        rightmove.discover(DiscoverQuery(), DiscoverLimits())

    zoopla = ZooplaHttpAdapter()
    assert zoopla.health().status.value == "disabled"

    checklist = Path("/opt/lampp/htdocs/verlox/keprix/docs/security/property-portal-legal-checklist.md")
    assert checklist.is_file()


def test_health_pack_high_risk_gate(store, monkeypatch):
    packs = load_vertical_packs(force=True)
    assert "health_social" in packs
    health = get_pack("health_social")
    sheet_ids = {st["id"] for st in health["sheet_types"]}
    assert {"clinic_referrals", "care_providers", "practitioners"} <= sheet_ids
    assert enroll_requires_soft_wall("health_social") is True

    # Soft Wall loosened workspace-wide, but high-risk enroll still blocks.
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    gate = gate_or_approve(
        "ws_a",
        kind="approve_list_enroll_high_risk",
        subject="Health enroll",
        payload={"list_id": "x"},
        always_require=True,
        force=True,
    )
    assert gate["blocked"] is True

    cqc = CqcApiAdapter()
    monkeypatch.delenv("CQC_API_KEY", raising=False)
    monkeypatch.delenv("KEPRIX_CQC_PUBLIC_MODE", raising=False)
    assert cqc.health().status.value == "not_configured"

    rows = [{"organisation": "Care Home A", "cqc_id": "1-123", "region": "Kent", "email": "ops@care.example"}]
    cands = HealthCsvAdapter().discover(
        DiscoverQuery(params={"rows": rows}, domain_pack="health_social"),
        DiscoverLimits(max_results=10),
    )
    assert len(cands) == 1
    assert cands[0].domain_pack == "health_social"
    assert "patient" in (cands[0].notes or "").lower() or "organisation" in (cands[0].notes or "").lower()

    with pytest.raises(RuntimeError, match="patient"):
        HealthCsvAdapter().discover(
            DiscoverQuery(params={"rows": [{"patient": "Alice", "nhs_number": "123"}]}),
            DiscoverLimits(),
        )


def test_registry_lists_vertical_adapters():
    reset_discovery_registry_for_tests()
    reg = get_discovery_registry()
    reg.ensure_builtin()
    names = set(reg.list_names())
    assert {
        "companies_house",
        "csv",
        "web_directory",
        "linkedin_api",
        "meta_graph",
        "tiktok_api",
        "social_csv_export",
        "property_csv",
        "rightmove_http",
        "zoopla_http",
        "cqc_api",
        "health_csv",
        "directory_web",
        "fake",
    } <= names

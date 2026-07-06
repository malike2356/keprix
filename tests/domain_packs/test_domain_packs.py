"""Prompt 30 domain knowledge pack factory tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.domain_packs.glossary import preserve_glossary_terms
from keprix.backend.domain_packs.localization import apply_localization, validate_localization_metadata
from keprix.backend.domain_packs.manifests import create_manifest_from_template
from keprix.backend.domain_packs.playbooks import validate_playbooks
from keprix.backend.domain_packs.schemas import DomainPackManifest, GlossaryTerm, PackSource
from keprix.backend.domain_packs.source_quality import source_quality_errors
from keprix.backend.domain_packs.store import reset_domain_pack_store
from keprix.backend.domain_packs.validation import validate_pack


@pytest.fixture
def domain_packs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_domain_pack_store(tmp_path / "domain_packs")
    import keprix.backend.localization.store as localization_store_module

    localization_store_module._store = None
    return tmp_path


def _sample_pack(**overrides) -> DomainPackManifest:
    pack = create_manifest_from_template("logistics", jurisdictions=["GH"])
    pack.sources = [
        PackSource(
            title="Ghana logistics guide",
            url="https://example.com/logistics",
            citation="Example Authority, Logistics Guide, 2025",
            jurisdiction="GH",
            retrieved_at="2026-01-01T00:00:00Z",
        )
    ]
    pack.glossary = [
        GlossaryTerm(term="waybill", definition="Document accompanying goods in transit.", locale="en")
    ]
    pack.playbooks = [{"title": "Onboarding", "href": "https://example.com/playbooks/onboarding"}]
    pack.localization_coverage = {"locales": ["en"], "fallback": "en"}
    for key, value in overrides.items():
        setattr(pack, key, value)
    return pack


def test_pack_manifest_validates(domain_packs_env) -> None:
    pack = _sample_pack()
    result = validate_pack(pack)
    assert result.ok is True


def test_missing_jurisdiction_fails_for_regulated_pack(domain_packs_env) -> None:
    pack = _sample_pack(domain_name="healthcare", jurisdictions=[], review_required=True)
    result = validate_pack(pack, for_publish=True)
    assert result.ok is False
    assert any("jurisdiction" in error for error in result.errors)


def test_source_without_citation_fails_quality_check(domain_packs_env) -> None:
    pack = _sample_pack()
    pack.sources = [PackSource(title="Guide", url="https://example.com", citation="")]
    errors = source_quality_errors(pack)
    assert any("citation" in error for error in errors)


def test_glossary_terms_are_preserved(domain_packs_env) -> None:
    existing = [GlossaryTerm(term="waybill", definition="Original", locale="en")]
    incoming = [GlossaryTerm(term="consignment", definition="Shipment batch", locale="en")]
    merged = preserve_glossary_terms(existing, incoming)
    terms = {row.term for row in merged}
    assert "waybill" in terms
    assert "consignment" in terms


def test_playbook_links_are_valid(domain_packs_env) -> None:
    pack = _sample_pack(playbooks=[{"title": "Broken", "href": "ftp://bad"}])
    errors = validate_playbooks(pack)
    assert any("invalid href" in error for error in errors)


def test_localization_metadata_validates(domain_packs_env) -> None:
    pack = _sample_pack(localization_coverage={})
    errors = validate_localization_metadata(pack)
    assert any("locales" in error for error in errors)
    pack = apply_localization(pack, locales=["en", "tw"], fallback="en")
    assert validate_localization_metadata(pack) == []


def test_high_stakes_pack_requires_disclaimer_and_review_gate(domain_packs_env) -> None:
    pack = _sample_pack(domain_name="legal", jurisdictions=["UK"], disclaimers=[], cannot_do=[])
    result = validate_pack(pack, for_publish=True)
    assert result.ok is False
    assert any("disclaimer" in error or "cannot do" in error or "review" in error for error in result.errors)


@pytest.mark.asyncio
async def test_create_and_validate_api(domain_packs_env) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/domain-packs",
            json={"domain_name": "agriculture", "jurisdictions": ["GH"]},
        )
        assert created.status_code == 200
        pack_id = created.json()["pack"]["id"]
        updated = await client.put(
            f"/api/domain-packs/{pack_id}",
            json={
                "sources": [
                    {
                        "title": "Ag guide",
                        "url": "https://example.com/ag",
                        "citation": "Ministry of Food and Agriculture, 2025",
                    }
                ],
                "glossary": [{"term": "acreage", "definition": "Land area under cultivation", "locale": "en"}],
                "playbooks": [{"title": "Season planning", "href": "https://example.com/playbooks/season"}],
            },
        )
        assert updated.status_code == 200
        localized = await client.post(
            f"/api/domain-packs/{pack_id}/localize",
            json={"locales": ["en", "tw"], "fallback": "en"},
        )
        assert localized.status_code == 200
        validated = await client.post(f"/api/domain-packs/{pack_id}/validate")
        assert validated.status_code == 200

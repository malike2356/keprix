from keprix.research.osint.entity import Entity
from keprix.research.osint.orchestrator import investigate


def test_investigation_correlates_normalized_identifier_and_cites():
    entity = Entity("company", "Example Ltd", seed={"company_number": "123"})
    result = investigate(
        workspace_id="ws1",
        entity=entity,
        acknowledge_lawful_use=True,
        sources={
            "registry": lambda _: [{"company_number": "123", "claim": "Active", "url": "https://registry.test/123"}],
            "sec": lambda _: [{"company_number": "123", "claim": "Filing", "url": "https://sec.test/123"}],
        },
    )
    assert result["status"] == "complete"
    assert result["report"]["correlations"]
    assert all(claim["source_url"] for claim in result["report"]["claims"])


def test_investigation_fails_closed_and_respects_depth_cap():
    entity = Entity("domain", "example.test")
    assert investigate(workspace_id="ws1", entity=entity, sources={}, acknowledge_lawful_use=False)["status"] == "acknowledgement_required"
    result = investigate(workspace_id="ws1", entity=entity, sources={}, acknowledge_lawful_use=True, depth_cap=1)
    assert result["status"] == "no_sources"


def test_investigation_expands_identifiers_between_rounds():
    entity = Entity("company", "Example Ltd")
    seen: list[set[str]] = []

    def source(current: Entity):
        seen.append(set(current.identifiers))
        if len(seen) == 1:
            return [{"company_number": "123", "claim": "Registry match", "url": "https://registry.test/123"}]
        return [{"company_number": "123", "domain": "example.test", "claim": "Website match", "url": "https://example.test"}]

    result = investigate(
        workspace_id="ws1", entity=entity, sources={"source": source},
        acknowledge_lawful_use=True, depth_cap=2,
    )
    assert result["rounds"] == 2
    assert len(seen) == 2
    assert "company_number:123" in seen[1]
    assert result["report"]["uncited_claims_omitted"] == 0


def test_correlation_requires_two_distinct_sources():
    entity = Entity("company", "Example Ltd")
    result = investigate(
        workspace_id="ws1", entity=entity,
        sources={"one": lambda _: [{"company_number": "123", "claim": "One", "url": "https://one.test"}]},
        acknowledge_lawful_use=True,
    )
    assert result["report"]["correlations"] == []

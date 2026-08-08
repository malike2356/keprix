"""CRM store isolation, upsert, provenance, and merge suggestion tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.crm.identity import IdentityResolver
from keprix.crm.models import CrmStage, ProvenanceKind
from keprix.crm.store import ConflictError, reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_account_lead_contact_deal_crud(store) -> None:
    account = store.create_account(
        "ws_a",
        "Acme Ltd",
        company_number="12345678",
        domain="acme.example",
        email="hello@acme.example",
        tags=["b2b"],
        scores={"fit": 0.8},
    )
    assert account["workspace_id"] == "ws_a"
    assert account["stage"] == CrmStage.DISCOVERED
    assert account["emails"][0]["address"] == "hello@acme.example"
    assert account["version"] == 1

    lead = store.create_lead(
        "ws_a",
        name="Acme opportunity",
        account_id=account["id"],
        company_number="12345678",
        email="sales@acme.example",
        source="companies_house",
    )
    contact = store.create_contact(
        "ws_a",
        "Ada Lovelace",
        account_id=account["id"],
        email="ada@acme.example",
        stage=CrmStage.ENRICHED,
    )
    deal = store.create_deal(
        "ws_a",
        "Acme pilot",
        account_id=account["id"],
        contact_id=contact["id"],
        lead_id=lead["id"],
        amount=1200,
    )
    assert deal["currency"] == "GBP"

    updated = store.update_lead("ws_a", lead["id"], stage=CrmStage.LISTED, expected_version=1)
    assert updated and updated["stage"] == CrmStage.LISTED
    assert updated["version"] == 2

    with pytest.raises(ConflictError):
        store.update_lead("ws_a", lead["id"], stage=CrmStage.APPROVED, expected_version=1)

    store.delete_contact("ws_a", contact["id"])
    assert store.get_contact("ws_a", contact["id"]) is None


def test_cross_workspace_read_fails_closed(store) -> None:
    lead = store.create_lead("ws_a", name="Only A", email="a@example.com")
    assert store.get_lead("ws_b", lead["id"]) is None
    assert store.list_leads("ws_b") == []
    assert store.update_lead("ws_b", lead["id"], name="hack") is None
    assert store.delete_lead("ws_b", lead["id"]) is None
    # Original still intact in owning workspace.
    assert store.get_lead("ws_a", lead["id"])["name"] == "Only A"


def test_idempotent_upsert_keys(store) -> None:
    first = store.upsert_contact("ws_a", display_name="Ada", email="Ada@Example.com")
    second = store.upsert_contact("ws_a", display_name="Ada L", email="ada@example.com")
    assert first["id"] == second["id"]
    assert second["display_name"] == "Ada L"

    a1 = store.upsert_account("ws_a", name="Acme", company_number="999")
    a2 = store.upsert_account("ws_a", name="Acme Renamed", company_number="999")
    assert a1["id"] == a2["id"]

    l1 = store.upsert_lead("ws_a", name="L1", external_source_id="ch:999")
    l2 = store.upsert_lead("ws_a", name="L2", external_source_id="ch:999")
    assert l1["id"] == l2["id"]
    assert l2["name"] == "L2"


def test_list_membership_activity_consent_suppression(store) -> None:
    lead = store.create_lead("ws_a", name="Lead", email="lead@example.com")
    lst = store.create_list("ws_a", "Q3 targets", domain_pack="generic")
    membership = store.add_list_member(
        "ws_a",
        lst["id"],
        member_type="lead",
        member_id=lead["id"],
        stage=CrmStage.LISTED,
    )
    assert membership["list_id"] == lst["id"]
    assert len(store.list_memberships("ws_a", lst["id"])) == 1

    activity = store.create_activity(
        "ws_a",
        entity_type="lead",
        entity_id=lead["id"],
        activity_type="note",
        body="Called",
        channel="phone",
    )
    assert activity["entity_id"] == lead["id"]

    consent = store.create_consent_record(
        "ws_a",
        subject_type="contact",
        subject_id="c1",
        channel="email",
        purpose="b2b_outreach",
        lawful_basis="legitimate_interest",
    )
    assert consent["jurisdiction"] == "UK"

    supp = store.create_suppression_entry(
        "ws_a",
        channel="email",
        address="nope@example.com",
        reason="unsubscribe",
    )
    assert store.is_suppressed("ws_a", channel="email", address="nope@example.com")
    assert not store.is_suppressed("ws_b", channel="email", address="nope@example.com")
    # Idempotent suppression
    again = store.create_suppression_entry(
        "ws_a",
        channel="email",
        address="NOPE@example.com",
        reason="unsubscribe",
    )
    assert again["id"] == supp["id"]


def test_provenance_and_merge_suggestion_shapes(store) -> None:
    contact = store.create_contact("ws_a", "Ada", email="ada@example.com")
    source = store.create_source_record(
        "ws_a",
        adapter="csv",
        external_id="row-1",
        content_hash="abc",
        snapshot={"email": "ada@example.com"},
    )
    prov = store.record_provenance(
        "ws_a",
        entity_type="contact",
        entity_id=contact["id"],
        field_name="emails",
        value=contact["emails"],
        kind=ProvenanceKind.OBSERVED,
        source_record_id=source["id"],
        adapter="csv",
        confidence=1.0,
        evidence_excerpt="row email",
    )
    assert prov["kind"] == "observed"
    assert prov["value"] == contact["emails"]
    listed = store.list_provenance("ws_a", entity_type="contact", entity_id=contact["id"])
    assert len(listed) == 1

    other = store.create_contact("ws_a", "Ada Lovelace", email="ada.l@example.com")
    suggestion = store.create_merge_suggestion(
        "ws_a",
        entity_type="contact",
        left_id=contact["id"],
        right_id=other["id"],
        match_keys=["name_fuzzy"],
        score=0.8,
        explanation="similar names",
        field_diff={"display_name": {"left": "Ada", "right": "Ada Lovelace"}},
    )
    assert suggestion["status"] == "pending"
    assert "field_diff" in suggestion
    pending = store.list_merge_suggestions("ws_a")
    assert len(pending) == 1
    assert pending[0]["id"] == suggestion["id"]


def test_outbox_idempotency_and_operator_types(store) -> None:
    row = store.enqueue_outbox(
        "ws_a",
        kind="send_email",
        idempotency_key="camp1:ada@example.com:step1",
        payload={"to": "ada@example.com"},
        entity_type="contact",
        entity_id="c1",
    )
    again = store.enqueue_outbox(
        "ws_a",
        kind="send_email",
        idempotency_key="camp1:ada@example.com:step1",
        payload={"to": "other@example.com"},
    )
    assert row["id"] == again["id"]
    assert again["payload"]["to"] == "ada@example.com"

    remembered = store.remember_idempotency(
        "ws_a",
        scope="enroll",
        idempotency_key="list1:lead1",
        result={"enrollment_id": "e1"},
    )
    assert store.get_idempotency("ws_a", scope="enroll", idempotency_key="list1:lead1")["id"] == remembered["id"]
    assert store.get_idempotency("ws_b", scope="enroll", idempotency_key="list1:lead1") is None

    job = store.create_discovery_job("ws_a", "companies_house", params={"query": "acme"})
    assert job["status"] == "queued"
    assert job["params"]["query"] == "acme"

    decision = store.upsert_contactability(
        "ws_a",
        subject_type="contact",
        subject_id="c1",
        channel="email",
        purpose="b2b_outreach",
        decision="deny",
        reason="no lawful basis",
    )
    assert decision["decision"] == "deny"

    ready = store.upsert_sender_readiness("ws_a", "acme.example", verified=True, spf_ok=True)
    assert ready["verified"] is True

    ks = store.upsert_kill_switch("ws_a", scope="workspace", enabled=True, reason="complaint spike")
    assert store.is_kill_switch_on("ws_a", scope="workspace") is True
    store.upsert_kill_switch("ws_a", scope="workspace", enabled=False)
    assert store.is_kill_switch_on("ws_a", scope="workspace") is False
    assert ks["scope"] == "workspace"


def test_identity_resolver_exact_and_fuzzy(store) -> None:
    resolver = IdentityResolver(store)
    contact = resolver.upsert_with_identity(
        "ws_a",
        "contact",
        display_name="Ada",
        email="ada@example.com",
    )
    match = resolver.resolve_contact("ws_a", email="ADA@example.com")
    assert match is not None
    assert match.entity_id == contact["id"]
    assert "email" in match.match_keys

    store.create_contact("ws_a", "Ada Lovelace", email="other@example.com")
    suggestions = resolver.suggest_fuzzy_merges(
        "ws_a",
        entity_type="contact",
        name="Ada",
        persist=True,
        min_score=0.7,
    )
    assert suggestions
    assert suggestions[0]["status"] == "pending"
    assert suggestions[0]["field_diff"]

    applied = resolver.apply_merge_suggestion(
        "ws_a",
        suggestions[0]["id"],
        survivor_id=suggestions[0]["left_id"],
        actor_type="user",
        actor_id="tester",
    )
    assert applied["survivor_id"] == suggestions[0]["left_id"]
    assert store.get_contact("ws_a", applied["merged_id"]) is None
    # Consent must remain addressable by original subject id conceptually:
    # merge must not rewrite consent subject_id onto survivor.
    consent = store.create_consent_record(
        "ws_a",
        subject_type="contact",
        subject_id=applied["merged_id"],
        channel="email",
        purpose="b2b_outreach",
        lawful_basis="consent",
    )
    assert consent["subject_id"] == applied["merged_id"]

"""Nice P5 CRM tests (prompts 453-465)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    from keprix.crm.store import CrmStore

    return CrmStore(tmp_path / "nice.sqlite")


def test_453_round_robin_lock_sla(store, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.crm import assignment as asn

    ws = "ws453"
    team = asn.ensure_team(store, ws, name="SDR", member_user_ids=["u1", "u2", "u3"])
    lead = store.create_lead(ws, name="A", email="a@ex.com")
    a1 = asn.assign_owner(store, ws, entity_type="lead", entity_id=lead["id"], team_id=team["id"], mode="round_robin")
    a2_lead = store.create_lead(ws, name="B", email="b@ex.com")
    a2 = asn.assign_owner(store, ws, entity_type="lead", entity_id=a2_lead["id"], team_id=team["id"], mode="round_robin")
    a3_lead = store.create_lead(ws, name="C", email="c@ex.com")
    a3 = asn.assign_owner(store, ws, entity_type="lead", entity_id=a3_lead["id"], team_id=team["id"], mode="round_robin")
    owners = [a1["entity"]["owner_user_id"], a2["entity"]["owner_user_id"], a3["entity"]["owner_user_id"]]
    assert owners == ["u1", "u2", "u3"]

    lock1 = asn.acquire_lock(store, ws, entity_type="lead", entity_id=lead["id"], owner_user_id="u1")
    assert lock1["ok"] is True
    lock2 = asn.acquire_lock(store, ws, entity_type="lead", entity_id=lead["id"], owner_user_id="u2")
    assert lock2.get("conflict") is True

    claim_lead = store.create_lead(ws, name="Claim me", email="claim@ex.com")
    claimed = asn.assign_owner(
        store, ws, entity_type="lead", entity_id=claim_lead["id"], mode="claim", actor_id="claimer"
    )
    assert claimed["ok"] is True
    assert claimed["entity"]["owner_user_id"] == "claimer"
    again = asn.assign_owner(
        store, ws, entity_type="lead", entity_id=claim_lead["id"], mode="claim", actor_id="other"
    )
    assert again.get("ok") is False
    assert again.get("error") == "already_assigned"

    comment = asn.add_comment(
        store, ws, entity_type="lead", entity_id=lead["id"], body="Ping @u2", mentions=["u2"], actor_id="u1"
    )
    assert "u2" in comment["mentions"]
    assert "in_app" in comment["notification"]["channels"]

    inbox = asn.sla_inbox(store, ws)
    assert inbox["counts"]["unassigned"] >= 0
    # Force overdue
    with store._lock:
        store._conn.execute(
            "UPDATE crm_leads SET sla_due_at = '2000-01-01T00:00:00+00:00', owner_user_id = 'u1' WHERE id = ?",
            (lead["id"],),
        )
        store._conn.commit()
    overdue = asn.sla_inbox(store, ws)
    assert overdue["counts"]["overdue"] >= 1


def test_453_paying_deal_reassign_soft_wall(store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    from keprix.crm import assignment as asn

    ws = "ws453pay"
    deal = store.create_deal(ws, name="Paying deal", stage="paying")
    blocked = asn.assign_owner(
        store,
        ws,
        entity_type="deal",
        entity_id=deal["id"],
        owner_user_id="new-owner",
        mode="manual",
        actor_id="mgr",
    )
    assert blocked.get("blocked") is True
    forced = asn.assign_owner(
        store,
        ws,
        entity_type="deal",
        entity_id=deal["id"],
        owner_user_id="new-owner",
        mode="manual",
        actor_id="mgr",
        force=True,
    )
    assert forced.get("ok") is True
    assert forced["entity"]["owner_user_id"] == "new-owner"


def test_454_csv_preview_and_not_configured(store) -> None:
    from keprix.crm import integrations as integ

    csv_text = "email,first_name,last_name,company\na@ex.com,Ann,Lee,Acme\nb@ex.com,Bob,Ray,Beta\n"
    preview = integ.preview_import(store, "ws454", provider="ghl", payload=csv_text)
    assert preview["ok"] is True
    assert preview["counts"]["create"] == 2
    applied = integ.apply_import(store, "ws454", provider="csv", payload=csv_text, force=True)
    assert applied["ok"] is True
    assert applied["created"] == 2
    # Re-import stable external ids / emails -> update
    again = integ.preview_import(store, "ws454", provider="csv", payload=csv_text)
    assert again["counts"]["update"] == 2
    hs = integ.get_adapter("hubspot").status()
    assert hs["status"] == "not_configured"


def test_455_sticky_and_guard_pause(store) -> None:
    from keprix.crm import experiments as exp

    ws = "ws455"
    e = exp.create_experiment(
        store,
        ws,
        name="Subject test",
        variants=[{"id": "A", "subject": "Hi"}, {"id": "B", "subject": "Hello"}],
        traffic_split={"A": 0.5, "B": 0.5},
        min_sample=10,
        guard_thresholds={"complaint_rate": 0.01, "unsub_rate": 0.02},
    )
    exp.start_experiment(store, ws, e["id"])
    v1 = exp.assign_variant(store, ws, e["id"], "contact-1")
    v2 = exp.assign_variant(store, ws, e["id"], "contact-1")
    assert v1 == v2
    # Trip guard
    for _ in range(5):
        exp.record_metric(store, ws, e["id"], variant=v1, metric="send")
    exp.record_metric(store, ws, e["id"], variant=v1, metric="complaint")
    paused = exp.get_experiment(store, ws, e["id"])
    assert paused["status"] == "paused_guard"
    results = exp.results_table(store, ws, e["id"])
    assert results["sample_warning"] is True


def test_456_fake_provider_provenance_and_reject(store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_FAKE_ENRICH_ALWAYS", "1")
    from keprix.crm import licensed_enrich as le

    ws = "ws456"
    lead = store.create_lead(ws, name="Blank", email=None)
    # Ensure no email
    with store._lock:
        store._conn.execute("UPDATE crm_leads SET emails = '[]' WHERE id = ?", (lead["id"],))
        store._conn.commit()
    proposed = le.propose_enrich(
        store,
        ws,
        provider="fake_licensed",
        batch=[{"entity_type": "lead", "entity_id": lead["id"], "fields": {"email": None, "phone": None}}],
    )
    assert proposed["ok"] is True
    rejected = le.reject_enrich(store, ws, proposed["run_id"])
    assert rejected["status"] == "rejected"
    lead2 = store.create_lead(ws, name="Blank2")
    with store._lock:
        store._conn.execute("UPDATE crm_leads SET emails = '[]' WHERE id = ?", (lead2["id"],))
        store._conn.commit()
    proposed2 = le.propose_enrich(
        store,
        ws,
        provider="fake_licensed",
        batch=[{"entity_type": "lead", "entity_id": lead2["id"], "fields": {"email": None}}],
    )
    applied = le.apply_enrich(store, ws, proposed2["run_id"], force=True)
    assert applied["ok"] is True
    assert applied["applied"] >= 1
    prov = store.list_provenance(ws, entity_type="lead", entity_id=lead2["id"])
    assert any(str(p.get("adapter") or "").startswith("provider:") for p in prov)
    missing = le.PROVIDERS["clearbit_slot"].enrich_contacts([])
    assert missing["status"] == "not_configured"

    # Overwrite blocked: non-empty email is skipped
    lead3 = store.create_lead(ws, name="HasEmail", email="keep@example.com")
    proposed3 = le.propose_enrich(
        store,
        ws,
        provider="fake_licensed",
        batch=[{"entity_type": "lead", "entity_id": lead3["id"], "fields": {"email": "keep@example.com"}}],
    )
    # Force a patch that would overwrite if apply ignored empty-cell rule
    with store._lock:
        store._conn.execute(
            "UPDATE crm_enrich_provider_runs SET patches_json = ? WHERE id = ?",
            (
                __import__("json").dumps(
                    [
                        {
                            "entity_type": "lead",
                            "entity_id": lead3["id"],
                            "field": "email",
                            "value": "overwrite@example.com",
                            "source": "provider:fake_licensed",
                            "evidence": {"url": "https://x", "id": "x"},
                        }
                    ]
                ),
                proposed3["run_id"],
            ),
        )
        store._conn.commit()
    applied3 = le.apply_enrich(store, ws, proposed3["run_id"], force=True)
    assert applied3["ok"] is True
    assert applied3.get("skipped_overwrite", 0) >= 1
    refreshed = store.get_lead(ws, lead3["id"])
    emails = refreshed.get("emails") or []
    addrs = [(e.get("address") if isinstance(e, dict) else e) for e in emails]
    assert "keep@example.com" in addrs
    assert "overwrite@example.com" not in addrs


def test_457_stale_conflict_reverify_soft_wall(store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    from keprix.crm import data_quality as dq
    from keprix.crm.models import ProvenanceKind

    ws = "ws457"
    lead = store.create_lead(ws, name="Q")
    store.record_provenance(
        ws,
        entity_type="lead",
        entity_id=lead["id"],
        field_name="phone",
        value="+441",
        kind=ProvenanceKind.OBSERVED,
        adapter="src_a",
        verification_state="unverified",
        observed_at="2000-01-01T00:00:00+00:00",
    )
    store.record_provenance(
        ws,
        entity_type="lead",
        entity_id=lead["id"],
        field_name="phone",
        value="+442",
        kind=ProvenanceKind.OBSERVED,
        adapter="src_b",
        verification_state="unverified",
        observed_at="2000-01-01T00:00:00+00:00",
    )
    summary = dq.quality_summary(store, ws)
    assert summary["counts"]["conflicts"] >= 1
    assert summary["counts"]["stale"] >= 1
    job = dq.create_reverify_job(store, ws, filters={})
    assert job.get("blocked") is True


def test_458_locale_fallback_and_soft_wall(store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    from keprix.crm import multilingual as ml

    ws = "ws458"
    blocked = ml.upsert_locale_variant(
        store,
        ws,
        sequence_id="seq1",
        step_order=1,
        locale="fr-FR",
        subject="Bonjour",
        body="Salut",
    )
    assert blocked.get("blocked") is True
    published = ml.upsert_locale_variant(
        store,
        ws,
        sequence_id="seq1",
        step_order=1,
        locale="fr-FR",
        subject="Bonjour",
        body="Salut",
        force=True,
    )
    assert published["ok"] is True
    fr = ml.resolve_step_copy(store, ws, sequence_id="seq1", step_order=1, preferred_locale="fr-FR")
    assert fr["ok"] is True
    assert fr["locale"] == "fr-FR"
    fb = ml.resolve_step_copy(
        store,
        ws,
        sequence_id="seq1",
        step_order=1,
        preferred_locale="de-DE",
        default_step={"subject": "Hi", "body": "Hello"},
    )
    assert fb["ok"] is True
    assert fb["fallback_used"] is True


def test_459_whatsapp_flag_and_consent(store, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.crm import messaging_channels as msg

    ws = "ws459"
    lead = store.create_lead(ws, name="M", email="m@ex.com")
    store.create_consent_record(
        ws,
        subject_type="lead",
        subject_id=lead["id"],
        channel="email",
        purpose="marketing",
        lawful_basis="consent",
    )
    monkeypatch.delenv("KEPRIX_WHATSAPP_SMS", raising=False)
    refused = msg.send_channel_message(
        store,
        ws,
        channel="sms",
        subject_type="lead",
        subject_id=lead["id"],
        address="+44000",
        body="hi",
        force=True,
    )
    assert refused["error"] == "feature_flag_off"

    monkeypatch.setenv("KEPRIX_WHATSAPP_SMS", "1")
    monkeypatch.setenv("KEPRIX_TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setenv("KEPRIX_TWILIO_ACCOUNT_SID", "sid")
    msg.enable_workspace_channels(store, ws, enabled=True, force=True)
    no_consent = msg.send_channel_message(
        store,
        ws,
        channel="sms",
        subject_type="lead",
        subject_id=lead["id"],
        address="+44000",
        body="hi",
        force=True,
        first_touch=False,
    )
    assert no_consent["error"] == "missing_channel_consent"


def test_460_tracking_default_off(store) -> None:
    from keprix.crm import tracking as tr

    ws = "ws460"
    off = tr.wrap_links(store, ws, html_or_text="See https://example.com/a")
    assert off["enabled"] is False
    assert "kpx_t" not in off["body"] and "/api/crm/tracking/click" not in off["body"]
    tr.set_workspace_tracking(store, ws, True)
    on = tr.wrap_links(store, ws, html_or_text="See https://example.com/a", campaign_id="c1", contact_key="k1")
    assert on["enabled"] is True
    assert on["wrapped_count"] == 1
    assert on["disclosure"]
    # wrap once
    again = tr.wrap_links(store, ws, html_or_text=on["body"], campaign_id="c1", contact_key="k1")
    assert again["wrapped_count"] == 0
    ev = tr.record_event(store, ws, event_type="click", token=on["body"].split("t=")[-1].split()[0], campaign_id="c1")
    assert ev["buying_signal"] is False


def test_461_social_unconfigured_and_scrape_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LINKEDIN_CLIENT_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    from keprix.discovery.adapters.social import LinkedInApiAdapter, scrape_refusal_payload
    from keprix.discovery.models import AdapterHealthStatus

    health = LinkedInApiAdapter().health()
    assert health.status == AdapterHealthStatus.NOT_CONFIGURED
    refuse = scrape_refusal_payload("linkedin")
    assert refuse["refused"] is True


def test_462_voice_and_retention(store, tmp_path: Path) -> None:
    from keprix.crm import voice_notes as vn
    from keprix.crm.data_quality import upsert_nice_settings

    ws = "ws462"
    upsert_nice_settings(store, ws, voice_consent_required=True, voice_retention_days=0)
    lead = store.create_lead(ws, name="Voice")
    unlinked = vn.attach_voice_note(store, ws, entity_type=None, entity_id=None, media_path="/tmp/x.ogg")
    assert unlinked["error"] == "unlinked_chat"
    media_file = tmp_path / "note.ogg"
    media_file.write_bytes(b"ogg")
    created = vn.attach_voice_note(
        store,
        ws,
        entity_type="lead",
        entity_id=lead["id"],
        media_path=str(media_file),
        stt_configured=True,
        consent_recorded=True,
    )
    assert created["ok"] is True
    assert created["activity"]["activity_type"] == "voice_note"
    # Expire retention
    with store._lock:
        store._conn.execute(
            "UPDATE crm_voice_media SET retention_until = '2000-01-01T00:00:00+00:00' WHERE id = ?",
            (created["media"]["id"],),
        )
        store._conn.commit()
    cleaned = vn.run_retention_job(store, ws)
    assert cleaned["deleted"] >= 1
    assert not media_file.exists()


def test_463_icp_score_deterministic(store, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.crm import icp as icp_mod
    from keprix.crm import icp_scoring as scoring

    ws = "ws463"
    icp = icp_mod.create_icp(
        store,
        ws,
        name="Score ICP",
        keywords=["plumb"],
        include_rules=[{"field": "keyword", "value": "leeds"}],
    )
    icp_mod.activate_icp(store, ws, icp["id"], force=True)
    lead = store.create_lead(ws, name="Leeds Plumbing Co", company_name="Leeds Plumbing Co")
    a = scoring.score_entity(store, ws, entity_type="lead", entity_id=lead["id"])
    b = scoring.score_entity(store, ws, entity_type="lead", entity_id=lead["id"])
    assert a["ok"] and b["ok"]
    assert a["icp_score"] == b["icp_score"]
    brief = scoring.generate_account_brief(store, ws, entity_type="lead", entity_id=lead["id"])
    assert brief["ok"] is True
    assert "evidence" in brief["brief"]
    sorted_leads = scoring.sort_leads_by_icp(store, ws)
    assert sorted_leads[0]["id"] == lead["id"]


def test_464_portal_checklist_and_kill(store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_PROPERTY_PORTAL_ADAPTERS", "0")
    from keprix.crm import property_portal_gate as pg

    ws = "ws464"
    status = pg.portal_gate_status(store, ws)
    assert status["acknowledged"] is False
    assert status["can_enable_jobs"] is False
    monkeypatch.setenv("KEPRIX_PROPERTY_PORTAL_ADAPTERS", "1")
    ack = pg.acknowledge_checklist(store, ws, acknowledged_by="owner", force=True)
    assert ack["ok"] is True
    ok = pg.assert_portal_job_allowed(store, ws)
    assert ok["ok"] is True
    pg.set_kill_switch(True)
    blocked = pg.assert_portal_job_allowed(store, ws)
    assert blocked["error"] == "kill_switch"
    pg.set_kill_switch(False)


def test_465_attribution_rules(store) -> None:
    from keprix.crm import attribution as attr

    ws = "ws465"
    deal = store.create_deal(ws, name="D1", amount=100)
    set_ok = attr.set_deal_attribution(store, ws, deal["id"], mode="influenced", notes="touched")
    assert set_ok["ok"] is True
    closed = store.create_deal(ws, name="D2", amount=200, tags=["vanity_sends_only"])
    attr.set_deal_attribution(store, ws, closed["id"], mode="closed")
    report = attr.attribution_report(store, ws)
    assert report["by_mode"]["influenced"]["count"] >= 1
    assert report["vanity_excluded"] >= 1
    assert attr.assignment_rules_check("influenced", has_touch=True, is_closed_won=False, vanity_only=False) == "influenced"
    assert attr.assignment_rules_check("sourced", has_touch=False, is_closed_won=True, vanity_only=True) == "reject_vanity"

"""Tests for email auth / deliverability helpers (shared policy parity)."""

from __future__ import annotations

import pytest

from keprix.email.deliverability_auth import (
    POLICY,
    DeliveryStore,
    classify_bounce,
    configure_marketing_domain,
    configure_transactional_domain,
    delivery_health_check,
    enforce_domain_separation,
    generate_dkim_record,
    generate_dmarc_record,
    generate_spf_record,
    validate_dns_records,
    warm_up_domain,
)


def test_generate_spf_dkim_dmarc() -> None:
    spf = generate_spf_record("mail.example.com", ["resend"])
    assert "v=spf1" in spf["value"]
    assert "_spf.resend.com" in spf["value"]
    dkim = generate_dkim_record("mail.example.com", "mail")
    assert "PRIVATE KEY" in dkim["private_key_pem"]
    assert "v=DKIM1" in dkim["record"]["value"]
    dmarc = generate_dmarc_record("mail.example.com", "none", rua="dmarc@example.com")
    assert "p=none" in dmarc["value"]
    assert POLICY["thresholds"]["spamComplaintRateMaxPct"] == 0.1


def test_validate_dns_injectable() -> None:
    def resolver(name: str) -> list[str]:
        if name == "mail.example.com":
            return ["v=spf1 include:_spf.resend.com ~all"]
        if name == "mail._domainkey.mail.example.com":
            return ["v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA"]
        if name == "_dmarc.mail.example.com":
            return ["v=DMARC1; p=none;"]
        return []

    result = validate_dns_records("mail.example.com", resolver=resolver)
    assert result["all_ok"] is True
    assert result["dmarc"]["policy"] == "none"


def test_domain_separation_and_warmup() -> None:
    tx = configure_transactional_domain("app.example.com")
    mkt = configure_marketing_domain("app.example.com")
    assert tx["sending_domain"] == "mail.app.example.com"
    assert mkt["sending_domain"] == "updates.app.example.com"
    with pytest.raises(ValueError, match="transactional"):
        enforce_domain_separation(
            "marketing",
            f"news@{tx['sending_domain']}",
            "app.example.com",
        )
    plan = warm_up_domain(tx["sending_domain"])
    assert plan["days"][0]["daily_cap"] == 50
    assert any(d["daily_cap"] >= 100 for d in plan["days"])


def test_delivery_health_alerts() -> None:
    store = DeliveryStore()
    domain = "mail.example.com"
    for i in range(100):
        store.track(
            f"e{i}",
            domain,
            "delivered" if i < 97 else "complained",
            at="2026-08-05T12:00:00+00:00",
        )
    health = delivery_health_check(
        store,
        domain,
        since="2026-08-01T00:00:00+00:00",
        until="2026-08-10T00:00:00+00:00",
    )
    assert any(a["code"] == "spam_complaint_high" for a in health["alerts"])
    assert classify_bounce("550 5.1.1 user unknown") == "hard"
    assert classify_bounce("blocked by spamhaus") == "block"

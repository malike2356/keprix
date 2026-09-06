from __future__ import annotations

from keprix.crm.compliance import evaluate_domain_message_policy
from keprix.discovery.materialize import enroll_requires_soft_wall
from keprix.discovery.packs import get_pack, load_vertical_packs


def test_copy_trading_pack_is_complete_and_high_risk() -> None:
    load_vertical_packs(force=True)
    pack = get_pack("copy-trading-mining")

    assert pack is not None
    assert pack["version"] == "1.0.0"
    assert pack["owner_review_required"] is True
    assert pack["high_risk_outreach"] is True
    assert pack["keywords"]
    assert pack["qualification_questions"]
    assert pack["message_bank"]
    assert pack["crm_stages"]
    assert enroll_requires_soft_wall("copy-trading-mining") is True
    assert "aiva" not in str(pack).lower()


def test_copy_trading_message_policy_blocks_claims_and_missing_disclaimer() -> None:
    blocked = evaluate_domain_message_policy(
        "Earn a guaranteed return with no risk.",
        domain_pack="copy-trading-mining",
    )
    assert blocked["decision"] == "deny"
    assert "guaranteed_return_language" in blocked["reasons"]
    assert "risk_disclaimer_missing" in blocked["reasons"]


def test_copy_trading_message_policy_allows_reviewed_disclaimer() -> None:
    allowed = evaluate_domain_message_policy(
        "Capital is at risk. Past performance is not a reliable indicator of future results. "
        "Would an evidence-led overview be useful?",
        domain_pack="copy-trading-mining",
    )
    assert allowed["decision"] == "allow"
    assert allowed["reasons"] == []

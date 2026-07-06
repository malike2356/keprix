"""Tests for CODEX reviewer module."""

from __future__ import annotations

import pytest

from keprix.personas.codex.reviewer import (
    LAWYER_REVIEW_WARNING,
    LEGAL_INFORMATION_DISCLAIMER,
    CodexReviewer,
    RiskLevel,
    analyze_contract_text,
    score_clause_risk,
)


SAMPLE_CONTRACT = """
MUTUAL NON-DISCLOSURE AGREEMENT

1. Confidentiality. Each party shall keep information confidential.
2. Limitation of Liability. Except for fraud, liability is limited to fees paid in the prior 12 months.
3. Indemnity. Party B shall indemnify Party A for all losses arising from any breach without limit.
4. Governing Law. This agreement is governed by the laws of England and Wales.
5. Termination. Either party may terminate on 14 days notice.
6. Personal data will be processed by Party B as processor.
"""


@pytest.fixture
def reviewer() -> CodexReviewer:
    return CodexReviewer(workspace_id="ws-codex", user_id="user-codex")


def test_score_clause_risk_consistent_for_similar_clauses() -> None:
    assert score_clause_risk("Unlimited Liability", "unlimited liability for all losses") == RiskLevel.HIGH
    assert score_clause_risk("Confidentiality", "mutual confidentiality obligations") == RiskLevel.LOW


def test_analyze_contract_detects_clauses_and_missing_protections() -> None:
    clauses, missing, revisions, _ = analyze_contract_text(SAMPLE_CONTRACT, jurisdiction="England and Wales (UK)")
    names = {clause.name for clause in clauses}
    assert "Indemnity" in names
    assert "Governing Law" in names
    assert any("breach notification" in item.lower() for item in missing)


@pytest.mark.asyncio
async def test_review_includes_disclaimer_and_lawyer_warning(reviewer: CodexReviewer) -> None:
    review = await reviewer.review_contract(
        title="Sample NDA",
        text=SAMPLE_CONTRACT,
        store=False,
        index_to_rag=False,
    )
    assert review.disclaimer == LEGAL_INFORMATION_DISCLAIMER
    assert review.lawyer_warning == LAWYER_REVIEW_WARNING
    assert LAWYER_REVIEW_WARNING in review.markdown
    assert review.jurisdiction == "England and Wales (UK)"


@pytest.mark.asyncio
async def test_review_structured_output_with_risk_scores(reviewer: CodexReviewer) -> None:
    review = await reviewer.review_contract(
        title="Vendor Agreement",
        text=SAMPLE_CONTRACT + "\n7. This agreement shall auto-renew unless cancelled 5 days before renewal.",
        store=False,
        index_to_rag=False,
    )
    assert review.key_clauses
    assert all(clause.risk in {"Low", "Medium", "High"} for clause in review.key_clauses)
    assert review.summary
    assert review.bottom_line


@pytest.mark.asyncio
async def test_review_stores_workspace_document(reviewer: CodexReviewer) -> None:
    review = await reviewer.review_contract(title="Stored Contract", text=SAMPLE_CONTRACT, index_to_rag=False)
    assert review.document_id

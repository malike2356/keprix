"""Tests for CODEX drafter module."""

from __future__ import annotations

import pytest

from keprix.personas.codex.drafter import CodexDrafter, DOCUMENT_TEMPLATES, UK_STANDARD_CLAUSES
from keprix.personas.codex.reviewer import LAWYER_REVIEW_WARNING, LEGAL_INFORMATION_DISCLAIMER


@pytest.fixture
def drafter() -> CodexDrafter:
    return CodexDrafter(workspace_id="ws-codex", user_id="user-codex")


def test_supported_document_types(drafter: CodexDrafter) -> None:
    types = drafter.supported_document_types()
    assert "nda" in types
    assert "privacy_policy" in types


def test_draft_includes_standard_uk_clauses(drafter: CodexDrafter) -> None:
    draft = drafter.draft_document(
        document_type="service_agreement",
        title="Master Services Agreement",
        jurisdiction="England and Wales (UK)",
        store=False,
    )
    assert draft.clauses_included
    for clause in UK_STANDARD_CLAUSES:
        assert clause in draft.clauses_included
    assert "England and Wales (UK)" in draft.content


def test_draft_includes_disclaimer(drafter: CodexDrafter) -> None:
    draft = drafter.draft_document(
        document_type="nda",
        title="Mutual NDA",
        store=False,
    )
    assert LEGAL_INFORMATION_DISCLAIMER in draft.content
    assert LAWYER_REVIEW_WARNING in draft.content


def test_privacy_policy_has_data_protection_clauses(drafter: CodexDrafter) -> None:
    draft = drafter.draft_document(document_type="privacy_policy", title="Privacy Policy", store=False)
    assert "lawful_bases_uk_gdpr" in draft.clauses_included
    assert "data_subject_rights" in draft.clauses_included


def test_unsupported_document_type_raises(drafter: CodexDrafter) -> None:
    with pytest.raises(ValueError):
        drafter.draft_document(document_type="unknown_doc", title="X", store=False)


def test_draft_stores_document(drafter: CodexDrafter) -> None:
    draft = drafter.draft_document(document_type="contractor_agreement", title="Contractor Agreement")
    assert draft.document_id
    assert draft.document_type in DOCUMENT_TEMPLATES

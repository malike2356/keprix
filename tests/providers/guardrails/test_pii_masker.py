"""Tests for guardrails/pii_masker.py."""

from __future__ import annotations

import pytest

from keprix.providers.guardrails.pii_masker import PIIMasker


@pytest.fixture
def masker():
    return PIIMasker()


def test_email_masked(masker):
    text, records = masker.mask("Contact us at hello@example.com today.")
    assert "[EMAIL]" in text
    assert "hello@example.com" not in text
    assert any(r.type == "EMAIL" for r in records)


def test_phone_us_masked(masker):
    text, _ = masker.mask("Call me at 415-555-1234 anytime.")
    assert "[PHONE]" in text
    assert "415-555-1234" not in text


def test_ipv4_masked(masker):
    text, _ = masker.mask("Server is at 192.168.1.100.")
    assert "[IP]" in text


def test_credit_card_masked(masker):
    text, _ = masker.mask("Card: 4111 1111 1111 1111.")
    assert "[CARD]" in text


def test_ssn_masked(masker):
    text, _ = masker.mask("SSN is 123-45-6789.")
    assert "[SSN]" in text


def test_bearer_token_masked(masker):
    text, _ = masker.mask("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123")
    assert "[TOKEN]" in text


def test_no_pii_unchanged(masker):
    clean = "Hello, how are you today?"
    text, records = masker.mask(clean)
    assert text == clean
    assert records == []


def test_unmask_restores_original(masker):
    original = "Email me at alice@example.com please."
    masked, records = masker.mask(original)
    assert masked != original
    restored = masker.unmask(masked, records)
    assert restored == original


def test_mask_messages_processes_all(masker):
    messages = [
        {"role": "user", "content": "My email is test@example.com"},
        {"role": "assistant", "content": "Got it, test@example.com noted."},
    ]
    cleaned, records = masker.mask_messages(messages)
    for msg in cleaned:
        assert "test@example.com" not in msg["content"]
    assert len(records) >= 2


def test_has_pii_detects(masker):
    assert masker.has_pii("Contact alice@example.com")
    assert not masker.has_pii("No sensitive data here.")


def test_multiple_pii_in_one_text(masker):
    text = "email: bob@test.com, ip: 10.0.0.1"
    masked, records = masker.mask(text)
    assert "[EMAIL]" in masked
    assert "[IP]" in masked
    assert len(records) == 2

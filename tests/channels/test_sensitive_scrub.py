"""Tests for TTS secret scrubbing."""

from __future__ import annotations

from keprix.channels.sensitive_scrub import scrub_secrets_for_speech, sensitive_field_warning


def test_scrub_telegram_token_shape():
    text = "Your token is 123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw thanks"
    out = scrub_secrets_for_speech(text)
    assert "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw" not in out
    assert "[redacted]" in out


def test_scrub_label_value_pairs():
    text = "bot_token: supersecretvalue123 and password=anothersecret99"
    out = scrub_secrets_for_speech(text)
    assert "supersecretvalue123" not in out
    assert "anothersecret99" not in out


def test_scrub_extra_caller_values():
    secret = "my-spoken-secret-value"
    out = scrub_secrets_for_speech(f"Got it, you said {secret}", extra_values=[secret])
    assert secret not in out


def test_sensitive_warning():
    assert "type" in sensitive_field_warning(field_label="bot token").lower()

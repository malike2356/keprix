"""Browser safety tests."""

from keprix.browser.safety import redact_text, requires_approval


def test_submit_requires_approval() -> None:
    assert requires_approval("submit")
    assert not requires_approval("read_page")


def test_redact_secrets_from_log_text() -> None:
    raw = "api_key=super-secret-token password=abc123 user@example.com"
    redacted = redact_text(raw)
    assert "super-secret-token" not in redacted
    assert "abc123" not in redacted
    assert "user@example.com" not in redacted
    assert "[REDACTED]" in redacted

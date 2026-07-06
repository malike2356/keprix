"""Secret scanner tests."""

from keprix.security.secret_scan import SecretScanner


def test_secret_scanner_redacts_before_storage():
    scanner = SecretScanner()
    text = "token sk-12345678901234567890123456789012"
    sanitized = scanner.scan_and_sanitize(text)
    assert "sk-12345678901234567890123456789012" not in sanitized
    assert "[REDACTED:api_key]" in sanitized


def test_secret_scanner_audit_callback():
    fired: list[str] = []

    def audit(_text: str, patterns: list[str]) -> None:
        fired.extend(patterns)

    scanner = SecretScanner(audit_callback=audit)
    scanner.scan_and_sanitize("PASSWORD=abc123")
    assert fired

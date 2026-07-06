"""Redactor tests."""

from keprix.security.redactor import Redactor


def test_api_key_redacted():
    redactor = Redactor()
    text = "Use key sk-12345678901234567890123456789012 here"
    result = redactor.redact(text)
    assert "sk-12345678901234567890123456789012" not in result
    assert "[REDACTED:api_key]" in result


def test_private_key_block_redacted():
    redactor = Redactor()
    text = "-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----"
    result = redactor.redact(text)
    assert "BEGIN RSA PRIVATE KEY" not in result
    assert "[REDACTED:private_key]" in result


def test_jwt_redacted():
    redactor = Redactor()
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"
    result = redactor.redact(token)
    assert "[REDACTED:jwt]" in result


def test_connection_string_password_redacted():
    redactor = Redactor()
    text = "postgres://user:secretpass@localhost:5432/db"
    result = redactor.redact(text)
    assert "secretpass" not in result
    assert "[REDACTED:password]" in result


def test_secret_env_assignment_redacted():
    redactor = Redactor()
    text = "PASSWORD=supersecret"
    result = redactor.redact(text)
    assert "supersecret" not in result
    assert "[REDACTED:secret]" in result

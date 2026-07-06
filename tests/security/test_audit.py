"""Audit log tests."""

from keprix.security.audit import hash_ip


def test_hash_ip_never_returns_raw_ip():
    raw = "203.0.113.10"
    hashed = hash_ip(raw)
    assert raw not in hashed
    assert len(hashed) == 64


def test_hash_ip_stable_for_same_input(monkeypatch):
    monkeypatch.setenv("KEPRIX_IP_HASH_SALT", "test-salt")
    from keprix.config.settings import get_settings

    get_settings.cache_clear()
    first = hash_ip("10.0.0.1")
    second = hash_ip("10.0.0.1")
    assert first == second

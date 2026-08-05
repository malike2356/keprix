"""Credential cache tests."""

from __future__ import annotations

from keprix.proxy.cache import CredentialCache, parse_duration_seconds
from keprix.proxy.secret import Secret


def test_parse_duration_seconds() -> None:
    assert parse_duration_seconds("60s") == 60
    assert parse_duration_seconds("2m") == 120
    assert parse_duration_seconds("1h") == 3600
    assert parse_duration_seconds("1d") == 86400


def test_cache_reuses_until_invalidated() -> None:
    cache = CredentialCache()
    calls = {"count": 0}

    def fetch() -> tuple[Secret, str]:
        calls["count"] += 1
        return Secret(f"value-{calls['count']}"), f"hash-{calls['count']}"

    first, _, cached_first = cache.get("ref", ttl_seconds=60, fetch=fetch)
    second, _, cached_second = cache.get("ref", ttl_seconds=60, fetch=fetch)
    assert first.expose() == "value-1"
    assert second.expose() == "value-1"
    assert cached_first is False
    assert cached_second is True
    assert calls["count"] == 1

    assert cache.invalidate("ref") == 1
    third, _, cached_third = cache.get("ref", ttl_seconds=60, fetch=fetch)
    assert third.expose() == "value-2"
    assert cached_third is False

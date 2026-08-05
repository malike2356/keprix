"""Trusted-proxy client IP resolution."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from keprix.security.client_ip import client_ip, is_https_request, trusted_proxy_cidrs


class _Req:
    def __init__(self, peer: str | None, headers: dict[str, str], scheme: str = "http"):
        self.client = SimpleNamespace(host=peer) if peer else None
        self.headers = headers
        self.url = SimpleNamespace(scheme=scheme)


def test_ignores_forwarded_without_trusted_proxies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEPRIX_TRUSTED_PROXIES", raising=False)
    req = _Req("203.0.113.9", {"x-forwarded-for": "198.51.100.7"})
    assert client_ip(req) == "203.0.113.9"
    assert trusted_proxy_cidrs() == []


def test_honors_forwarded_from_trusted_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_TRUSTED_PROXIES", "127.0.0.1,::1")
    req = _Req("127.0.0.1", {"x-forwarded-for": "198.51.100.7, 10.0.0.1"})
    assert client_ip(req) == "198.51.100.7"


def test_rejects_spoofed_forwarded_from_untrusted_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_TRUSTED_PROXIES", "127.0.0.1")
    req = _Req("203.0.113.9", {"x-forwarded-for": "198.51.100.7"})
    assert client_ip(req) == "203.0.113.9"


def test_https_via_trusted_proto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_TRUSTED_PROXIES", "127.0.0.1")
    req = _Req("127.0.0.1", {"x-forwarded-proto": "https"}, scheme="http")
    assert is_https_request(req) is True
    req2 = _Req("203.0.113.9", {"x-forwarded-proto": "https"}, scheme="http")
    assert is_https_request(req2) is False


def test_trust_all_proxies_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_TRUSTED_PROXIES", "fly=any")
    req = _Req("203.0.113.9", {"x-forwarded-for": "198.51.100.7"})
    assert client_ip(req) == "198.51.100.7"

"""Tests for SSRF denylist."""

from __future__ import annotations

import pytest

from keprix.proxy.ssrf import assert_host_allowed, is_private_or_loopback_ip


def test_private_ip_detection():
    assert is_private_or_loopback_ip("127.0.0.1")
    assert is_private_or_loopback_ip("10.0.0.5")
    assert not is_private_or_loopback_ip("8.8.8.8")


def test_assert_host_allowed_blocks_localhost():
    with pytest.raises(PermissionError, match="private or loopback"):
        assert_host_allowed("127.0.0.1")

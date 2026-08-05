"""Tests for security/egress_policy.py."""

from __future__ import annotations

import pytest

from keprix.security.egress_policy import EgressPolicy


@pytest.fixture
def policy():
    p = EgressPolicy()
    p.load_product(
        "aiva",
        allowed_hosts={"api.sendgrid.com", "api.stripe.com", "*.googleapis.com"},
        extra_denied_hosts={"api.abbis.com"},
    )
    p.load_product(
        "abbis",
        allowed_hosts={"api.stripe.com"},
        extra_denied_hosts=set(),
    )
    return p


# --- Private IP protection (builtin, always enforced) ---

def test_loopback_always_blocked(policy):
    d = policy.is_allowed("aiva", "localhost", "127.0.0.1")
    assert not d.allowed
    # localhost is blocked by hostname check before IP check
    assert d.reason in ("private_ip_blocked", "private_hostname_blocked")


def test_private_rfc1918_blocked(policy):
    d = policy.is_allowed("aiva", "internal-db", "10.0.0.1")
    assert not d.allowed
    assert d.reason == "private_ip_blocked"


def test_aws_metadata_blocked(policy):
    d = policy.is_allowed("aiva", "169.254.169.254", "169.254.169.254")
    assert not d.allowed
    assert d.reason == "private_ip_blocked"


def test_172_16_range_blocked(policy):
    d = policy.is_allowed("aiva", "host", "172.20.0.1")
    assert not d.allowed


def test_192_168_range_blocked(policy):
    d = policy.is_allowed("aiva", "host", "192.168.1.100")
    assert not d.allowed


def test_localhost_hostname_blocked(policy):
    d = policy.is_allowed("aiva", "localhost", "127.0.0.1")
    assert not d.allowed


# --- Allowlist ---

def test_allowed_exact_host(policy):
    d = policy.is_allowed("aiva", "api.sendgrid.com", "167.89.0.1")
    assert d.allowed
    assert d.reason == "host_in_allowlist"


def test_wildcard_subdomain_allowed(policy):
    d = policy.is_allowed("aiva", "calendar.googleapis.com", "142.250.0.1")
    assert d.allowed


def test_wildcard_subdomain_drive_allowed(policy):
    d = policy.is_allowed("aiva", "drive.googleapis.com", "142.250.0.2")
    assert d.allowed


def test_wildcard_does_not_match_extra_subdomain(policy):
    # evil.googleapis.com.attacker.com should not match *.googleapis.com
    d = policy.is_allowed("aiva", "evil.googleapis.com.attacker.com", "1.2.3.4")
    assert not d.allowed


def test_wildcard_does_not_match_parent_domain(policy):
    # "googleapis.com" itself does not match "*.googleapis.com"
    d = policy.is_allowed("aiva", "googleapis.com", "142.250.0.3")
    assert not d.allowed


# --- Denied list override ---

def test_product_denied_host_blocked_even_if_not_in_allowlist(policy):
    d = policy.is_allowed("aiva", "api.abbis.com", "54.1.1.1")
    assert not d.allowed
    assert d.reason == "host_denied_by_policy"


# --- Default deny for unlisted hosts ---

def test_host_not_in_allowlist_denied(policy):
    d = policy.is_allowed("aiva", "evil.com", "104.1.1.1")
    assert not d.allowed
    assert d.reason == "host_not_in_allowlist"


def test_host_allowed_for_abbis(policy):
    d = policy.is_allowed("abbis", "api.stripe.com", "54.187.0.1")
    assert d.allowed


def test_host_not_allowed_for_abbis(policy):
    d = policy.is_allowed("abbis", "api.sendgrid.com", "167.89.0.1")
    assert not d.allowed


# --- Unknown product ---

def test_unknown_product_denied(policy):
    d = policy.is_allowed("phantom", "api.stripe.com", "54.187.0.1")
    assert not d.allowed
    assert d.reason == "unknown_product"


# --- Default allow mode ---

def test_default_allow_mode_permits_unknown_host():
    p = EgressPolicy()
    p.load_product("internal_tool", allowed_hosts=set(), default_deny=False)
    d = p.is_allowed("internal_tool", "some-internal-service.lan", "203.0.113.1")
    assert d.allowed
    assert d.reason == "default_allow"


# --- Snapshot ---

def test_snapshot_contains_all_products(policy):
    snap = policy.snapshot()
    assert "aiva" in snap
    assert "abbis" in snap
    assert "*.googleapis.com" in snap["aiva"]["allowed_hosts"]

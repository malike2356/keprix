"""EgressPolicy: per-product network egress control.

Every product declares which external hosts it may reach. Requests to
undeclared hosts are blocked before the TCP connection is made.

Built-in denied ranges (private/loopback) are always enforced and cannot
be removed by any product configuration.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any


# Hardcoded private ranges that no product may ever reach.
# These protect against SSRF to cloud metadata endpoints and internal services.
_BUILTIN_DENIED_CIDRS: list[str] = [
    "169.254.0.0/16",   # AWS/GCP/Azure metadata
    "10.0.0.0/8",       # RFC1918 private
    "172.16.0.0/12",    # RFC1918 private
    "192.168.0.0/16",   # RFC1918 private
    "127.0.0.0/8",      # loopback
    "::1/128",          # IPv6 loopback
    "fc00::/7",         # IPv6 unique local
]

_BUILTIN_DENIED_HOSTNAMES: frozenset[str] = frozenset({"localhost", "metadata.google.internal"})


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: str


@dataclass
class ProductEgressRules:
    default_deny: bool = True
    allowed_hosts: set[str] = field(default_factory=set)
    extra_denied_hosts: set[str] = field(default_factory=set)


def _cidr_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Build the built-in denied network list once."""
    nets = []
    for cidr in _BUILTIN_DENIED_CIDRS:
        try:
            nets.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            pass
    return nets


_BUILTIN_NETS = _cidr_networks()


def _ip_is_private(ip_str: str) -> bool:
    """Return True if ip_str falls within any built-in denied CIDR."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        # Non-parseable IP strings are treated as private (fail closed)
        return True
    return any(addr in net for net in _BUILTIN_NETS)


def _host_matches_pattern(host: str, pattern: str) -> bool:
    """Return True if host matches pattern.

    Patterns:
      "api.sendgrid.com"    - exact hostname match
      "*.googleapis.com"    - single subdomain wildcard; matches one level only
                              (calendar.googleapis.com matches; sub.cal.googleapis.com does not)
    """
    if pattern.startswith("*."):
        suffix = pattern[1:]   # ".googleapis.com"
        if not host.endswith(suffix):
            return False
        prefix = host[: -len(suffix)]
        # prefix must be non-empty and contain no dots (one label only)
        return len(prefix) > 0 and "." not in prefix
    return host == pattern


def _host_matches_any(host: str, patterns: set[str]) -> bool:
    return any(_host_matches_pattern(host, p) for p in patterns)


class EgressPolicy:
    """Registry of per-product outbound HTTP egress rules.

    Usage::

        policy = EgressPolicy()
        policy.load_product("aiva",
            allowed_hosts={"api.sendgrid.com", "*.googleapis.com"},
            extra_denied_hosts=set(),
        )
        decision = policy.is_allowed("aiva", "api.sendgrid.com", "167.89.0.1")
    """

    def __init__(self) -> None:
        self._policies: dict[str, ProductEgressRules] = {}

    def load_product(
        self,
        product_id: str,
        allowed_hosts: set[str] | list[str] | None = None,
        extra_denied_hosts: set[str] | list[str] | None = None,
        default_deny: bool = True,
    ) -> None:
        """Register or replace egress rules for a product."""
        self._policies[product_id] = ProductEgressRules(
            default_deny=default_deny,
            allowed_hosts=set(allowed_hosts or []),
            extra_denied_hosts=set(extra_denied_hosts or []),
        )

    def is_allowed(self, product_id: str, host: str, ip: str) -> EgressDecision:
        """Return an EgressDecision for an outbound request.

        Args:
            product_id: The product making the request.
            host: The destination hostname (from the URL).
            ip: The resolved IP address (after DNS lookup).
        """
        # Built-in protection: always block private/loopback ranges
        if host in _BUILTIN_DENIED_HOSTNAMES:
            return EgressDecision(allowed=False, reason="private_hostname_blocked")

        if _ip_is_private(ip):
            return EgressDecision(allowed=False, reason="private_ip_blocked")

        # Unknown product: fail closed
        rules = self._policies.get(product_id)
        if rules is None:
            return EgressDecision(allowed=False, reason="unknown_product")

        # Product's extra denied hosts override everything
        if _host_matches_any(host, rules.extra_denied_hosts):
            return EgressDecision(allowed=False, reason="host_denied_by_policy")

        # Default allow mode: any host not explicitly blocked is fine
        if not rules.default_deny:
            return EgressDecision(allowed=True, reason="default_allow")

        # Default deny mode: must be in allowlist
        if _host_matches_any(host, rules.allowed_hosts):
            return EgressDecision(allowed=True, reason="host_in_allowlist")

        return EgressDecision(allowed=False, reason="host_not_in_allowlist")

    def list_products(self) -> list[str]:
        return list(self._policies.keys())

    def snapshot(self) -> dict[str, Any]:
        return {
            pid: {
                "default_deny": r.default_deny,
                "allowed_hosts": sorted(r.allowed_hosts),
                "extra_denied_hosts": sorted(r.extra_denied_hosts),
            }
            for pid, r in self._policies.items()
        }


_default_policy: EgressPolicy | None = None


def get_egress_policy() -> EgressPolicy:
    global _default_policy
    if _default_policy is None:
        _default_policy = EgressPolicy()
    return _default_policy


def reset_egress_policy() -> None:
    global _default_policy
    _default_policy = None

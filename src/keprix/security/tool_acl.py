"""ToolACL: deny-by-default per-product tool access control list.

ACL decision hierarchy for every (product_id, tool_name) pair:

  1. Unknown product (not registered and not "keprix") -> UNKNOWN_PRODUCT
  2. Base product "keprix": allow unless tool is in denied_tools -> DENIED
  3. Other products: deny unless tool matches an allowed_tools pattern -> DENIED_NOT_LISTED
  4. Tool matches allowed_tools AND is not in denied_tools -> ALLOWED
  5. Tool matches both allowed_tools AND denied_tools -> DENIED

Pattern forms accepted in allowed_tools / denied_tools:
  - "*"               matches any tool
  - "category:*"      matches all tools whose name starts with "category:"
  - "category:name"   exact match

ACL check is a pure dictionary/set lookup: no I/O, no DB query, < 0.5 ms.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ACLDecision(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    DENIED_NOT_LISTED = "not_listed"
    UNKNOWN_PRODUCT = "unknown_product"


@dataclass
class ProductACL:
    """Resolved ACL config for one product."""
    product_id: str
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)


_DEFAULT_ALLOWLIST = [
    "check:*",
    "export:*",
    "get:*",
    "health:*",
    "list:*",
    "memory:read*",
    "query:*",
    "rag:*",
    "read:*",
    "search:*",
    "status:*",
    "usage:*",
]

_DEFAULT_DENYLIST = [
    "code_exec:*",
    "code-exec:*",
    "credential:*",
    "credentials:*",
    "email:send*",
    "file:delete*",
    "file:write*",
    "git:*",
    "install:*",
    "mail:send*",
    "network:*",
    "terminal:run",
    "terminal:*",
    "vault:dump*",
]

_PROFILE_ALLOWLISTS: dict[str, list[str]] = {
    "assistant": list(_DEFAULT_ALLOWLIST),
    "researcher": [
        "check:*",
        "export:*",
        "get:*",
        "health:*",
        "list:*",
        "query:*",
        "read:*",
        "search:*",
        "status:*",
        "usage:*",
        "web:search*",
    ],
    "operator": [
        "check:*",
        "export:*",
        "file:read*",
        "file:write*",
        "get:*",
        "health:*",
        "list:*",
        "query:*",
        "read:*",
        "search:*",
        "status:*",
        "usage:*",
    ],
}

_PROFILE_DENYLISTS: dict[str, list[str]] = {
    "assistant": list(_DEFAULT_DENYLIST),
    "researcher": [
        "email:send*",
        "file:write*",
        "mail:send*",
        "terminal:*",
        "vault:dump*",
    ],
    "operator": [
        "email:send*",
        "mail:send*",
        "vault:dump*",
    ],
}


def _env_tool_patterns(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _matches(pattern: str, tool_name: str) -> bool:
    """Return True if pattern matches tool_name.

    Patterns:
      "*"           -> any tool
      "foo:*"       -> any tool whose name starts with "foo:"
      "foo:bar"     -> exact match
    """
    if pattern == "*":
        return True
    if pattern.endswith(":*"):
        prefix = pattern[:-1]  # e.g. "crm:"
        return tool_name.startswith(prefix)
    return pattern == tool_name


def _matches_any(patterns: list[str], tool_name: str) -> bool:
    return any(_matches(p, tool_name) for p in patterns)


class ToolACL:
    """Registry of per-product tool allowlists and denylists.

    Usage::

        acl = ToolACL()
        acl.load_product("aiva", allowed_tools=["crm:*", "search:web"], denied_tools=["terminal:run"])
        decision = acl.check("aiva", "terminal:run")
        # ACLDecision.DENIED

        decision = acl.check("aiva", "crm:create_contact")
        # ACLDecision.ALLOWED

    The base product ("keprix") is seeded with a curated allowlist and denylist.
    """

    BASE_PRODUCT = "keprix"

    def __init__(self) -> None:
        self._products: dict[str, ProductACL] = {}
        self._lock = asyncio.Lock()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        allow = _env_tool_patterns("KEPRIX_TOOL_ACL_DEFAULT_ALLOWLIST") or list(_DEFAULT_ALLOWLIST)
        deny = _env_tool_patterns("KEPRIX_TOOL_ACL_DEFAULT_DENYLIST") or list(_DEFAULT_DENYLIST)
        self._products[self.BASE_PRODUCT] = ProductACL(
            product_id=self.BASE_PRODUCT,
            allowed_tools=allow,
            denied_tools=deny,
        )

    def load_profile(self, product_id: str, profile: str) -> None:
        profile_key = (profile or "").strip().lower()
        if profile_key not in _PROFILE_ALLOWLISTS:
            raise ValueError(f"Unknown tool ACL profile: {profile}")
        self.load_product(
            product_id,
            allowed_tools=list(_PROFILE_ALLOWLISTS[profile_key]),
            denied_tools=list(_PROFILE_DENYLISTS.get(profile_key, [])),
        )

    def load_product(
        self,
        product_id: str,
        allowed_tools: list[str] | None = None,
        denied_tools: list[str] | None = None,
    ) -> None:
        """Register or replace ACL config for a product (synchronous, call at startup)."""
        self._products[product_id] = ProductACL(
            product_id=product_id,
            allowed_tools=list(allowed_tools or []),
            denied_tools=list(denied_tools or []),
        )

    async def load_product_async(
        self,
        product_id: str,
        allowed_tools: list[str] | None = None,
        denied_tools: list[str] | None = None,
    ) -> None:
        """Thread-safe version for use during live config reload."""
        async with self._lock:
            self.load_product(product_id, allowed_tools, denied_tools)

    def check(self, product_id: str, tool_name: str) -> ACLDecision:
        """Return the ACL decision for (product_id, tool_name).

        This method is synchronous and must complete in < 0.5 ms.
        """
        # Base product: deny by default, using the seeded allowlist and denylist.
        if product_id == self.BASE_PRODUCT:
            base = self._products.get(self.BASE_PRODUCT)
            if base and _matches_any(base.denied_tools, tool_name):
                return ACLDecision.DENIED
            if base and _matches_any(base.allowed_tools, tool_name):
                return ACLDecision.ALLOWED
            return ACLDecision.DENIED_NOT_LISTED

        # Unknown product
        if product_id not in self._products:
            return ACLDecision.UNKNOWN_PRODUCT

        acl = self._products[product_id]

        # Denied list overrides allow
        if _matches_any(acl.denied_tools, tool_name):
            return ACLDecision.DENIED

        # Not in allowlist
        if not _matches_any(acl.allowed_tools, tool_name):
            return ACLDecision.DENIED_NOT_LISTED

        return ACLDecision.ALLOWED

    def check_or_raise(self, product_id: str, tool_name: str) -> None:
        """Raise ToolACLDenied if the tool is not allowed; otherwise return None."""
        from .tool_acl_denied import ToolACLDenied

        decision = self.check(product_id, tool_name)
        if decision == ACLDecision.ALLOWED:
            return

        if decision == ACLDecision.DENIED_NOT_LISTED:
            reason = f"'{tool_name}' is not in the allowlist for product '{product_id}'"
        elif decision == ACLDecision.DENIED:
            reason = f"'{tool_name}' is explicitly denied for product '{product_id}'"
        else:
            reason = f"product '{product_id}' is not registered in the ACL"

        raise ToolACLDenied(
            product_id=product_id,
            tool_name=tool_name,
            reason=reason,
        )

    def resolved_tools(
        self,
        product_id: str,
        all_tool_names: list[str],
    ) -> dict[str, ACLDecision]:
        """Return the ACL decision for every known tool name.

        Used by CLI acl-check and the API route to show a full picture.
        """
        return {name: self.check(product_id, name) for name in all_tool_names}

    def list_registered_products(self) -> list[str]:
        return list(self._products.keys())

    def snapshot(self) -> dict[str, Any]:
        """Return a read-only summary of all registered product ACLs."""
        return {
            pid: {
                "allowed_tools": list(acl.allowed_tools),
                "denied_tools": list(acl.denied_tools),
            }
            for pid, acl in self._products.items()
        }


# Module-level singleton for use across the application
_default_acl: ToolACL | None = None


def get_tool_acl() -> ToolACL:
    """Return the module-level ToolACL instance, creating it on first call."""
    global _default_acl
    if _default_acl is None:
        _default_acl = ToolACL()
    return _default_acl


def reset_tool_acl() -> None:
    """Reset the module-level singleton (test helper)."""
    global _default_acl
    _default_acl = None

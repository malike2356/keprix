"""Safe retrieval boundaries for audience turns (Prompt 630)."""

from __future__ import annotations

import re
from typing import Any

from keprix.customer_concierge.audience.context import get_audience_context
from keprix.customer_concierge.audience.tool_policy import is_customer_concierge_tool_allowed

_INJECTION_HINTS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|call\s+shell|read\s+vault|"
    r"dump\s+brain|cat\s+/etc|workspace[_-]member)",
    re.I,
)


def sanitize_visitor_text(text: str) -> dict[str, Any]:
    """Mark prompt-injection style text; never expands tool allowlist."""
    raw = text or ""
    suspicious = bool(_INJECTION_HINTS.search(raw))
    return {
        "text": raw[:4000],
        "suspicious": suspicious,
        "toolsStillDenied": not is_customer_concierge_tool_allowed("shell-exec"),
    }


def forbidden_storage_access(target: str, *, require_audience: bool = True) -> bool:
    """True when an audience turn attempts private Brain/Vault/files/owner stores."""
    if require_audience and get_audience_context() is None:
        return False
    t = (target or "").strip().lower()
    if not t:
        return False
    blocked = (
        "brain",
        "vault",
        "document_vault",
        "document-vault",
        "private",
        "owner",
        "filesystem",
        "/api/fs",
        "credential",
        "billing",
    )
    return any(b in t for b in blocked)

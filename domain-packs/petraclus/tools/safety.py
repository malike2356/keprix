"""Safety helpers for Petraclus sidecar tools.

Scanner banners, findings and feed text are untrusted data, never tool instructions.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from nodes.catalog import FORBIDDEN_NODES

_INJECTION_RE = re.compile(
    r"(?:ignore\s+(?:previous|all)\s+instructions|system\s*prompt|you\s+are\s+now|"
    r"tool\s*call|execute\s+shell|browse\s+to|fetch\s+url|delete\s+all|"
    r"run\s+nmap|exploit|</?\s*(?:system|tool|function)\b)",
    re.I,
)

_SECRET_RE = re.compile(
    r"(?:api[_-]?key|password|secret|token|bearer\s+[a-z0-9._-]{8,}|-----BEGIN)",
    re.I,
)


def detect_prompt_injection(text: str) -> dict[str, Any]:
    raw = str(text or "")
    matches = [m.group(0) for m in _INJECTION_RE.finditer(raw)]
    return {
        "detected": bool(matches),
        "signals": sorted({m.lower() for m in matches}),
        "tool_instruction_allowed": False,
        "treated_as": "untrusted_scanner_or_feed_text",
    }


def sanitize_scanner_text(text: str, *, max_len: int = 4000) -> dict[str, Any]:
    raw = str(text or "")
    injection = detect_prompt_injection(raw)
    clipped = raw[:max_len]
    # Strip control chars except newline/tab
    cleaned = "".join(ch for ch in clipped if ch in "\n\t" or ord(ch) >= 32)
    return {
        "text": cleaned,
        "truncated": len(raw) > max_len,
        "injection": injection,
        "contains_secret_pattern": bool(_SECRET_RE.search(raw)),
    }


def is_blocked_internal_ip(value: str) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    if text in {"localhost", "metadata.google.internal"} or text.endswith((".local", ".internal")):
        return True
    try:
        ip = ipaddress.ip_address(text.split("%")[0])
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or str(ip) == "169.254.169.254"
    )


def assert_no_forbidden_nodes(node_key: str) -> None:
    if node_key in FORBIDDEN_NODES:
        raise PermissionError(f"forbidden_node:{node_key}")


def safe_log_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Return log-safe fields without tokens, findings text or raw evidence."""
    blocked = {
        "token",
        "access_token",
        "authorization",
        "password",
        "secret",
        "finding",
        "findings",
        "evidence",
        "raw_evidence",
        "description",
        "banner",
    }
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in blocked:
            out[key] = "[redacted]"
            continue
        if isinstance(value, str) and _SECRET_RE.search(value):
            out[key] = "[redacted]"
            continue
        out[key] = value
    return out

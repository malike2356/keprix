"""Redact secrets from trajectory payloads before persistence."""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(
    r"(?i)("
    r"(?:sk|pk|rk)-(?:live|test|proj)?[-_]?[a-z0-9]{16,}"
    r"|(?:api[_-]?key|access[_-]?token|bearer)\s*[:=]\s*[^\s\"']{12,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
    r")"
)

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "access_token",
        "refresh_token",
        "private_key",
        "sudo_password",
        "vault_secret",
        "credential",
        "credentials",
    }
)

_REDACTED = "[redacted]"


def redact_text(value: str) -> str:
    if not value:
        return value
    return _TOKEN_RE.sub(_REDACTED, value)


def redact_payload(payload: Any, *, depth: int = 0) -> Any:
    """Recursively redact sensitive keys and token-like strings."""
    if depth > 12:
        return _REDACTED
    if payload is None or isinstance(payload, (bool, int, float)):
        return payload
    if isinstance(payload, str):
        return redact_text(payload)
    if isinstance(payload, list):
        return [redact_payload(item, depth=depth + 1) for item in payload[:500]]
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in list(payload.items())[:200]:
            key_l = str(key).lower()
            if key_l in _SENSITIVE_KEYS or any(s in key_l for s in ("secret", "password", "token", "api_key")):
                out[str(key)] = _REDACTED
            else:
                out[str(key)] = redact_payload(value, depth=depth + 1)
        return out
    return redact_text(str(payload))

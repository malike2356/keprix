"""Browser action safety classification."""

from __future__ import annotations

import re
from typing import Any

RISKY_ACTIONS = {
    "submit",
    "send_message",
    "publish",
    "delete",
    "download_sensitive",
    "upload",
    "purchase",
    "change_settings",
    "modify_crm",
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]+", re.I),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
)


def requires_approval(action: str) -> bool:
    return action in RISKY_ACTIONS


def classify_action(action: str, *, selector: str = "") -> str:
    if requires_approval(action):
        return "approval_required"
    return "safe"


def redact_text(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            cleaned[key] = redact_text(value)
        else:
            cleaned[key] = value
    return cleaned

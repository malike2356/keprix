"""Secret redaction for logs and API responses."""

from __future__ import annotations

import os
import re

_REDACT_ENABLED = os.getenv("SECRET_REDACTION_ENABLED", "true").lower() in {"1", "true", "yes"}

_PREFIX_PATTERNS = [
    r"sk-ant-api03-[A-Za-z0-9_-]{10,}",
    r"sk-[A-Za-z0-9_-]{10,}",
    r"ghp_[A-Za-z0-9]{10,}",
    r"AIza[A-Za-z0-9_-]{30,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
]

_PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(" + "|".join(_PREFIX_PATTERNS) + r")(?![A-Za-z0-9_-])"
)

_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----"
)


def mask_secret(value: str) -> str:
    if len(value) <= 18:
        return "[REDACTED]"
    return f"{value[:6]}...[REDACTED]...{value[-4:]}"


def redact_text(text: str) -> str:
    if not _REDACT_ENABLED or not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        return mask_secret(match.group(1))

    text = _PREFIX_RE.sub(_replace, text)
    text = _PRIVATE_KEY_RE.sub("[REDACTED PRIVATE KEY]", text)
    return text


def redact_json(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_json(item) for key, item in value.items()}
    return value

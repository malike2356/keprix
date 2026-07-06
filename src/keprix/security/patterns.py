"""Shared regex patterns for redaction and secret scanning."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretPattern:
    name: str
    pattern: re.Pattern[str]
    replacement: str


def _compile(name: str, pattern: str, replacement: str) -> SecretPattern:
    return SecretPattern(name=name, pattern=re.compile(pattern, re.MULTILINE | re.DOTALL), replacement=replacement)


SECRET_PATTERNS: tuple[SecretPattern, ...] = (
    _compile(
        "api_key",
        r"(?i)\b(sk-[a-zA-Z0-9]{20,}|"
        r"sk-ant-[a-zA-Z0-9\-_]{20,}|"
        r"ghp_[a-zA-Z0-9]{20,}|"
        r"gho_[a-zA-Z0-9]{20,}|"
        r"ghu_[a-zA-Z0-9]{20,}|"
        r"ghs_[a-zA-Z0-9]{20,}|"
        r"ghr_[a-zA-Z0-9]{20,}|"
        r"xox[baprs]-[a-zA-Z0-9\-]{10,}|"
        r"AKIA[0-9A-Z]{16}|"
        r"AIza[0-9A-Za-z\-_]{35})\b",
        "[REDACTED:api_key]",
    ),
    _compile(
        "private_key",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "[REDACTED:private_key]",
    ),
    _compile(
        "jwt",
        r"\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b",
        "[REDACTED:jwt]",
    ),
    _compile(
        "connection_string",
        r"(?i)((?:postgres|postgresql|mysql|mongodb|redis)(?:\+[\w]+)?://[^:\s/]+:)([^@\s]+)(@[^\s]+)",
        r"\1[REDACTED:password]\3",
    ),
    _compile(
        "secret_env",
        r"(?i)\b((?:SECRET|KEY|TOKEN|PASSWORD|PASS)\s*=\s*)([^\s#]+)",
        r"\1[REDACTED:secret]",
    ),
    _compile(
        "private_ip",
        r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b",
        "[REDACTED:private_ip]",
    ),
)

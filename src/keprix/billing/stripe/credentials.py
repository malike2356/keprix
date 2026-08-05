"""Resolve Stripe credentials from environment or local credential files."""

from __future__ import annotations

import os
import re
from pathlib import Path

def _candidate_paths() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("KEPRIX_STRIPE_CREDENTIALS_FILE", "").strip()
    if explicit:
        paths.append(Path(explicit).expanduser())
    return paths


def _parse_credential_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    pattern = re.compile(r"^\s*(?:[-*]\s*)?`?([A-Z][A-Z0-9_]+)`?\s*(?::|=)\s*`?([^`\s#]+)")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip().strip("`").strip()
        if value and not value.startswith("<"):
            values[key] = value
    return values


def stripe_secret_key() -> str:
    for key in ("STRIPE_BILLING_SECRET_KEY", "STRIPE_SECRET_KEY", "STRIPE_SECRET"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    for path in _candidate_paths():
        values = _parse_credential_file(path)
        for key in ("STRIPE_BILLING_SECRET_KEY", "STRIPE_SECRET_KEY", "STRIPE_SECRET", "STRIPE_KEY"):
            value = values.get(key, "").strip()
            if value:
                return value
    return ""


def stripe_webhook_secret() -> str:
    for key in ("STRIPE_BILLING_WEBHOOK_SECRET", "STRIPE_WEBHOOK_SECRET"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    for path in _candidate_paths():
        values = _parse_credential_file(path)
        for key in ("STRIPE_BILLING_WEBHOOK_SECRET", "STRIPE_WEBHOOK_SECRET"):
            value = values.get(key, "").strip()
            if value:
                return value
    return ""


def stripe_credentials_configured() -> bool:
    return bool(stripe_secret_key())

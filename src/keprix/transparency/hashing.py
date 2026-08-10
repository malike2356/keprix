"""SHA-256 helpers for generation-log integrity (content itself is not stored)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_text(value: str | bytes | None) -> str:
    if value is None:
        data = b""
    elif isinstance(value, bytes):
        data = value
    else:
        data = str(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return sha256_text(payload)

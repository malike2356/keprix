"""Sensitive document logging helpers."""

from __future__ import annotations


def redact_for_log(text: str, *, preview_chars: int = 0) -> str:
    if preview_chars > 0:
        return f"[redacted:{len(text)} chars]"
    return "[redacted document content]"

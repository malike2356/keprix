"""Voice transcription to coding request normalization."""

from __future__ import annotations

import re


_PREFIX_RE = re.compile(
    r"^(?:hey keprix|hey khepri|okay keprix|please)\s*[,.]?\s*",
    re.I,
)


def voice_to_coding_request(transcript: str) -> str:
    text = transcript.strip()
    if not text:
        return ""
    text = _PREFIX_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if not text.endswith((".", "!", "?")):
        text += "."
    if not _looks_like_coding_request(text):
        text = f"Implement the following coding task: {text}"
    return text


def _looks_like_coding_request(text: str) -> bool:
    keywords = (
        "fix",
        "add",
        "update",
        "refactor",
        "rename",
        "create",
        "remove",
        "implement",
        "change",
        "replace",
        "write",
        "edit",
        "bug",
        "test",
        "function",
        "class",
        "file",
        "module",
    )
    lower = text.lower()
    return any(word in lower for word in keywords)

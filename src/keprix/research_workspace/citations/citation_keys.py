"""Stable citation key helpers."""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slug_author(author: str) -> str:
    text = unicodedata.normalize("NFKD", author)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.split(",")[0].split()[-1] if author else "anon"
    return _NON_ALNUM.sub("", text.lower()) or "anon"


def generate_citation_key(
    *,
    authors: list[str],
    year: str | None,
    title: str,
    preferred_key: str | None = None,
) -> str:
    if preferred_key:
        return preferred_key
    author_part = slug_author(authors[0]) if authors else "anon"
    year_part = (year or "nd")[:4]
    title_words = [word for word in re.split(r"\s+", title.lower()) if word.isalpha()]
    title_part = "".join(word[:4] for word in title_words[:2]) or "item"
    return f"{author_part}{year_part}{title_part}"

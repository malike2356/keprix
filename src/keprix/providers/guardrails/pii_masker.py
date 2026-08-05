"""PII detection and masking. Adapted from OmniRoute's piiMasker.ts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MaskRecord:
    type: str
    original: str
    replacement: str
    position: int  # position in the MASKED string (for unmask reconstruction)


_PATTERNS: list[tuple[str, str, str]] = [
    # (label, pattern, replacement)
    ("EMAIL",       r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',          "[EMAIL]"),
    ("PHONE_UK",    r'\b(?:\+44\s?|0)(?:7\d{3}|\d{2})\s?\d{3}\s?\d{4}\b',              "[PHONE]"),
    ("PHONE_US",    r'\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',            "[PHONE]"),
    ("IPV4",        r'\b(?:\d{1,3}\.){3}\d{1,3}\b',                                     "[IP]"),
    ("CREDIT_CARD", r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',                 "[CARD]"),
    ("SSN",         r'\b\d{3}-\d{2}-\d{4}\b',                                           "[SSN]"),
    ("API_KEY",     r'\b(?:sk-[A-Za-z0-9_\-]{20,}|[A-Za-z0-9_]{32,}(?:key|token)[A-Za-z0-9_]*)\b',
                                                                                         "[API_KEY]"),
    ("BEARER",      r'Bearer\s+[A-Za-z0-9_\-\.]{20,}',                                  "Bearer [TOKEN]"),
]

_COMPILED = [(label, re.compile(pat, re.IGNORECASE), repl) for label, pat, repl in _PATTERNS]


class PIIMasker:
    """Detect and mask PII in outgoing request text.

    Usage::

        masker = PIIMasker()
        masked_text, records = masker.mask(text)
        original = masker.unmask(masked_text, records)
    """

    def mask(self, text: str) -> tuple[str, list[MaskRecord]]:
        """Mask all detected PII in text. Returns (masked_text, records)."""
        records: list[MaskRecord] = []
        offset = 0  # track position shift from replacements

        for label, pattern, replacement in _COMPILED:
            new_text = text
            shift = 0
            for match in pattern.finditer(text):
                start = match.start() + shift
                end = match.end() + shift
                original = match.group()

                records.append(MaskRecord(
                    type=label,
                    original=original,
                    replacement=replacement,
                    position=start,
                ))

                new_text = new_text[:start] + replacement + new_text[end:]
                shift += len(replacement) - len(original)

            text = new_text

        return text, records

    def mask_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[MaskRecord]]:
        """Mask PII in all message content fields."""
        all_records: list[MaskRecord] = []
        result = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                masked, records = self.mask(content)
                all_records.extend(records)
                msg = dict(msg)
                msg["content"] = masked
            result.append(msg)
        return result, all_records

    def unmask(self, text: str, records: list[MaskRecord]) -> str:
        """Restore original values from mask records (used on response)."""
        for rec in sorted(records, key=lambda r: r.position, reverse=True):
            pos = rec.position
            repl_end = pos + len(rec.replacement)
            if text[pos:repl_end] == rec.replacement:
                text = text[:pos] + rec.original + text[repl_end:]
        return text

    def has_pii(self, text: str) -> bool:
        """Quick check: does text contain any detectable PII?"""
        return any(pat.search(text) for _, pat, _ in _COMPILED)

"""Shared validators for research workspace evals."""

from __future__ import annotations

import re

ALLOWED_OPINION_MARKERS = ("[analysis]", "[generated opinion]", "[hypothesis]")


def validate_report_claims(report_text: str, *, citation_keys: list[str]) -> list[str]:
    """Return uncited factual claim lines that lack citation keys or allowed markers."""
    issues: list[str] = []
    keys_pattern = "|".join(re.escape(key) for key in citation_keys) if citation_keys else None
    in_bibliography = False
    for line in report_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Bibliography") or stripped.startswith("# References"):
            in_bibliography = True
            continue
        if in_bibliography:
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^\d+\.\s+", stripped):
            continue
        if any(marker in stripped for marker in ALLOWED_OPINION_MARKERS):
            continue
        if keys_pattern and re.search(rf"\[({keys_pattern})\]", stripped):
            continue
        if re.search(r"\b\d+(\.\d+)?%?\b", stripped) or re.search(
            r"\b(rose|fell|increased|decreased|grew|declined)\b", stripped, re.I
        ):
            issues.append(stripped)
    return issues

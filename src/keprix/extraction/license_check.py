"""License and third-party obligation checks for extracted references."""

from __future__ import annotations

import re
from pathlib import Path

PROPRIETARY_MARKERS = [
    re.compile(r"(?i)all rights reserved"),
    re.compile(r"(?i)proprietary and confidential"),
    re.compile(r"(?i)commercial license only"),
    re.compile(r"(?i)not for redistribution"),
]

COPYLEFT_MARKERS = [
    re.compile(r"(?i)GNU Affero General Public License"),
    re.compile(r"(?i)AGPL"),
]

ALLOWED_LICENSE_HINTS = [
    "MIT",
    "Apache-2.0",
    "BSD",
    "ISC",
    "Python Software Foundation",
]


def check_text_license(text: str) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {
        "proprietary": [],
        "copyleft": [],
        "allowed": [],
    }
    for pattern in PROPRIETARY_MARKERS:
        if pattern.search(text):
            findings["proprietary"].append(pattern.pattern)
    for pattern in COPYLEFT_MARKERS:
        if pattern.search(text):
            findings["copyleft"].append(pattern.pattern)
    for hint in ALLOWED_LICENSE_HINTS:
        if hint.lower() in text.lower():
            findings["allowed"].append(hint)
    return findings


def check_file_license(path: Path) -> dict[str, list[str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:8000]
    except OSError:
        return {"proprietary": [], "copyleft": [], "allowed": []}
    return check_text_license(text)


def license_conflicts_with_keprix(findings: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    if findings.get("proprietary"):
        errors.append("proprietary license markers detected")
    if findings.get("copyleft") and not findings.get("allowed"):
        errors.append("copyleft license without explicit compatibility review")
    return errors

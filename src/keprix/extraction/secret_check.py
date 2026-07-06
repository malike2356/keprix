"""Secret pattern detection for extraction scans."""

from __future__ import annotations

import re
from pathlib import Path

from keprix.extraction.classifier import is_excluded_scan_path

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"rk_live_[a-zA-Z0-9]{20,}"),
    re.compile(r"pk_live_[a-zA-Z0-9]{20,}"),
]

REJECTED_SECRET_EXTENSIONS = {".pem", ".key", ".p12", ".pfx"}


def scan_text(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(pattern.pattern)
    return hits


def scan_file(path: Path) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {"secrets": [], "blocked_extensions": []}
    if path.suffix.lower() in REJECTED_SECRET_EXTENSIONS:
        findings["blocked_extensions"].append(path.suffix.lower())
        return findings
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings
    if scan_text(text):
        findings["secrets"].append(str(path))
    return findings


def scan_tree(root: Path, *, skip_excluded=is_excluded_scan_path) -> list[dict[str, list[str]]]:
    results: list[dict[str, list[str]]] = []
    if not root.exists():
        return results
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if skip_excluded(path):
            continue
        findings = scan_file(path)
        if findings["secrets"] or findings["blocked_extensions"]:
            results.append(findings)
    return results


def has_secret_content(text: str) -> bool:
    return bool(scan_text(text))

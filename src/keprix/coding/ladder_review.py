"""Ponytail review helpers for current diffs."""

from __future__ import annotations


def review_diff(diff_text: str) -> dict:
    findings: list[dict[str, object]] = []
    for index, line in enumerate(diff_text.splitlines(), start=1):
        lowered = line.lower()
        if line.startswith("+") and ("todo later" in lowered or "future-proof" in lowered):
            findings.append({"line": index, "tag": "yagni", "message": "Speculative future-proofing; cut it.", "confidence": "medium", "estimated_lines": 1})
        if line.startswith("+") and "import requests" in lowered:
            findings.append({"line": index, "tag": "stdlib", "message": "Prefer installed HTTP helper or stdlib unless requests already exists here.", "confidence": "medium", "estimated_lines": 1})
    return {"findings": findings, "summary": "Lean already. Ship." if not findings else f"{sum(int(item['estimated_lines']) for item in findings)} lines removable"}

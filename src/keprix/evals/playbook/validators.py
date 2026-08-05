"""Validators for NL playbook draft evals (Prompt 208)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from keprix.playbook.nl_builder import parse_playbook_yaml


def validate_draft_yaml(yaml_text: str, case: dict[str, Any]) -> list[str]:
    """Return validation issues for a generated playbook draft."""
    issues: list[str] = []
    if "n8n-nodes-base" in yaml_text:
        issues.append("output contains n8n-nodes-base")
    if "={{ $" in yaml_text:
        issues.append("output contains n8n expression syntax")

    try:
        parsed = parse_playbook_yaml(yaml_text)
    except ValueError as exc:
        return [str(exc)]

    step_types = {
        str(step.get("type") or "")
        for step in parsed.get("steps") or []
        if isinstance(step, dict)
    }
    for required in case.get("must_include_steps") or []:
        if required not in step_types:
            issues.append(f"missing required step type: {required}")

    blob = yaml_text.lower()
    for key in case.get("must_include_keys") or []:
        if str(key).lower() not in blob:
            issues.append(f"missing required id/key substring: {key}")

    if case.get("must_use_steps_template") and "{{ steps." not in yaml_text:
        issues.append("missing Keprix {{ steps.* }} references")

    for term in case.get("forbid_terms") or []:
        if re.search(rf"\b{re.escape(str(term))}\b", yaml_text, re.IGNORECASE):
            issues.append(f"forbidden term present: {term}")

    return issues


def load_eval_suite_cases(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        return []
    cases = payload.get("cases")
    return [case for case in cases if isinstance(case, dict)] if isinstance(cases, list) else []

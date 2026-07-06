"""Dataset validation rules."""

from __future__ import annotations

import re
from typing import Any

from keprix.research_workspace.datasets.codebook import Codebook

_RULE_RE = re.compile(r"^(required|min|max|regex):(.+)$")


def validate_row(row: dict[str, Any], codebook: Codebook) -> list[str]:
    errors: list[str] = []
    for variable in codebook.variables:
        value = row.get(variable.name)
        for rule in variable.validation_rules:
            match = _RULE_RE.match(rule)
            if not match:
                continue
            kind, payload = match.group(1), match.group(2)
            if kind == "required" and (value is None or str(value).strip() == ""):
                errors.append(f"{variable.name}: required")
            elif kind == "min" and value is not None:
                try:
                    if float(value) < float(payload):
                        errors.append(f"{variable.name}: below min {payload}")
                except ValueError:
                    errors.append(f"{variable.name}: not numeric for min rule")
            elif kind == "max" and value is not None:
                try:
                    if float(value) > float(payload):
                        errors.append(f"{variable.name}: above max {payload}")
                except ValueError:
                    errors.append(f"{variable.name}: not numeric for max rule")
            elif kind == "regex" and value is not None and not re.match(payload, str(value)):
                errors.append(f"{variable.name}: regex mismatch")
    return errors


def validate_sample(rows: list[dict[str, Any]], codebook: Codebook) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        row_errors = validate_row(row, codebook)
        if row_errors:
            issues.append({"row": index, "errors": row_errors})
    return {"checked_rows": len(rows), "issues": issues, "ok": not issues}

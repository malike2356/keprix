"""Guardrail helpers for crews and flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


GuardrailCallable = Callable[[Any], bool | tuple[bool, str]]


@dataclass(slots=True)
class GuardrailResult:
    passed: bool
    message: str = ""


def run_guardrails(output: Any, guardrails: list[GuardrailCallable] | None = None) -> GuardrailResult:
    for guardrail in guardrails or []:
        result = guardrail(output)
        if isinstance(result, tuple):
            passed, message = result
        else:
            passed, message = bool(result), ""
        if not passed:
            return GuardrailResult(False, message or "Guardrail failed")
    return GuardrailResult(True)

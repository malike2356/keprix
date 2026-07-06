"""Input and output guardrails for agent runs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Literal

from keprix.agents_runtime.agent_spec import AgentSpec
from keprix.security.redactor import get_redactor

GuardrailPhase = Literal["input", "output"]
GuardrailFn = Callable[[str, AgentSpec, dict[str, Any]], tuple[bool, str]]


@dataclass
class GuardrailResult:
    passed: bool
    message: str = ""
    guardrail: str = ""
    repair_hint: str = ""


FINANCIAL_PATTERN = re.compile(
    r"(?i)\b(refund|charge|wire|invoice|payment|credit card|bank account)\b"
)
LEGAL_MEDICAL_PATTERN = re.compile(
    r"(?i)\b(diagnos|prescri|legal advice|sue|lawsuit|attorney|malpractice)\b"
)
BROWSER_RISKY_PATTERN = re.compile(r"(?i)\b(click|navigate|submit form|purchase)\b")


def _secret_leakage(text: str, _spec: AgentSpec, _ctx: dict[str, Any]) -> tuple[bool, str]:
    redacted = get_redactor().redact(text)
    if redacted != text:
        return False, "Secret or credential pattern detected"
    return True, ""


def _financial_action(text: str, _spec: AgentSpec, _ctx: dict[str, Any]) -> tuple[bool, str]:
    if FINANCIAL_PATTERN.search(text) and "approved" not in _ctx:
        return False, "Financial action requires explicit approval"
    return True, ""


def _legal_medical(text: str, _spec: AgentSpec, _ctx: dict[str, Any]) -> tuple[bool, str]:
    if LEGAL_MEDICAL_PATTERN.search(text):
        return False, "Legal or medical advice must be escalated to a human"
    return True, ""


def _unsafe_browser(text: str, spec: AgentSpec, _ctx: dict[str, Any]) -> tuple[bool, str]:
    if "browser" in spec.tools and BROWSER_RISKY_PATTERN.search(text):
        return False, "Risky browser action blocked pending approval"
    return True, ""


def _tool_risk(text: str, _spec: AgentSpec, ctx: dict[str, Any]) -> tuple[bool, str]:
    blocked = set(ctx.get("blocked_tools") or [])
    for tool in blocked:
        if tool in text:
            return False, f"Tool {tool} is blocked by policy"
    return True, ""


def _output_schema(text: str, spec: AgentSpec, _ctx: dict[str, Any]) -> tuple[bool, str]:
    if not spec.output_schema:
        return True, ""
    try:
        payload = json.loads(text) if text.strip().startswith("{") else {"answer": text}
    except json.JSONDecodeError:
        return False, "Output must be valid JSON matching the agent schema"
    required = spec.output_schema.get("required") or []
    properties = spec.output_schema.get("properties") or {}
    if not properties and spec.output_schema.get("type") == "object":
        properties = spec.output_schema.get("properties") or {"answer": {}}
    if properties:
        for key in properties:
            if key not in payload and key in required:
                return False, f"Missing required output field: {key}"
    return True, ""


GUARDRAIL_REGISTRY: dict[str, GuardrailFn] = {
    "secret_leakage": _secret_leakage,
    "financial_action": _financial_action,
    "legal_medical": _legal_medical,
    "unsafe_browser": _unsafe_browser,
    "tool_risk": _tool_risk,
    "output_schema": _output_schema,
}


def run_guardrails(
    text: str,
    spec: AgentSpec,
    *,
    phase: GuardrailPhase,
    context: dict[str, Any] | None = None,
) -> GuardrailResult:
    ctx = dict(context or {})
    ctx["phase"] = phase
    for name in spec.guardrails:
        fn = GUARDRAIL_REGISTRY.get(name)
        if fn is None:
            continue
        passed, message = fn(text, spec, ctx)
        if not passed:
            return GuardrailResult(
                passed=False,
                message=message,
                guardrail=name,
                repair_hint="Revise the response to remove blocked content and try again.",
            )
    return GuardrailResult(passed=True)

"""LLM-powered tool code generator."""

from __future__ import annotations

import ast
import json
import logging
import re
import textwrap
from typing import Any

from keprix.agent.keprix.schemas import GapReport, SynthesisResult
from keprix.agent.keprix.synthesiser_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class SynthesisError(RuntimeError):
    """Raised when LLM synthesis or response parsing fails."""


class ToolSynthesiser:
    async def synthesise(self, gap: GapReport, *, rewrite_hint: str | None = None) -> SynthesisResult:
        tool_name = _normalize_tool_name(gap.candidate_tool_name or "generated_tool")
        description = gap.gap_description or f"Generated tool for: {gap.task}"
        try:
            return await self._synthesise_with_llm(
                gap=gap,
                tool_name=tool_name,
                description=description,
                rewrite_hint=rewrite_hint,
            )
        except SynthesisError as exc:
            logger.warning("LLM synthesis failed, using offline fallback: %s", exc)
            return self._fallback_synthesis(
                tool_name=tool_name,
                description=description,
                task=gap.task,
                rewrite_hint=rewrite_hint,
                candidate_tool_name=gap.candidate_tool_name,
            )

    async def _synthesise_with_llm(
        self,
        *,
        gap: GapReport,
        tool_name: str,
        description: str,
        rewrite_hint: str | None,
    ) -> SynthesisResult:
        from agent.auxiliary_client import async_call_llm, extract_content_or_reasoning

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    tool_name=tool_name,
                    description=description,
                    task=gap.task,
                    approach=gap.candidate_approach,
                    rewrite_hint=rewrite_hint,
                ),
            },
        ]
        try:
            response = await async_call_llm(
                task="mutation_synthesis",
                messages=messages,
                temperature=0.2,
                max_tokens=6000,
            )
        except Exception as exc:
            raise SynthesisError(f"LLM call failed: {exc}") from exc

        try:
            from keprix.usage.pricing_bridge import usage_from_response
            from keprix.usage.recorder import get_llm_usage_recorder

            usage = usage_from_response(response)
            model = getattr(response, "model", None) or "mutation_synthesis"
            await get_llm_usage_recorder().record(
                usage=usage,
                provider="mutation",
                model=str(model),
                channel="mutation",
                metadata={"tool_name": tool_name, "task": gap.task},
            )
        except Exception:
            pass

        raw = extract_content_or_reasoning(response).strip()
        if not raw:
            raise SynthesisError("LLM returned empty synthesis response")

        payload = _extract_json_payload(raw)
        if payload is None:
            raise SynthesisError("LLM response did not contain valid JSON")

        return _build_result_from_payload(payload, tool_name=tool_name, description=description)

    def _fallback_synthesis(
        self,
        *,
        tool_name: str,
        description: str,
        task: str,
        rewrite_hint: str | None,
        candidate_tool_name: str = "",
    ) -> SynthesisResult:
        if _is_stock_gap(task, tool_name, description):
            tool_code = self._render_stock_tool_code(tool_name, description, rewrite_hint=rewrite_hint)
            skill_yaml = self._render_stock_skill_yaml(tool_name, description)
            test_input = {"ticker": "AAPL"}
        elif _is_time_tracking_gap(task, tool_name, candidate_tool_name):
            tool_code = self._render_track_time_tool_code(tool_name, description, rewrite_hint=rewrite_hint)
            skill_yaml = self._render_track_time_skill_yaml(tool_name, description)
            test_input = {"project": "demo project", "action": "start"}
        else:
            tool_code = self._render_generic_tool_code(tool_name, description, task, rewrite_hint=rewrite_hint)
            skill_yaml = self._render_generic_skill_yaml(tool_name, description, task)
            test_input = _default_test_input(tool_name, task)

        return SynthesisResult(
            tool_name=tool_name,
            tool_code=tool_code,
            skill_yaml=skill_yaml,
            description=description,
            test_input=test_input,
        )

    def _render_stock_tool_code(self, tool_name: str, description: str, *, rewrite_hint: str | None = None) -> str:
        hint = f"\n# Rewrite note: {rewrite_hint}\n" if rewrite_hint else ""
        return textwrap.dedent(
            f'''
            """Generated tool: {tool_name}"""
            {hint}
            from tools.registry import registry, tool_result, tool_error

            _MOCK_PRICES = {{
                "AAPL": 213.42,
                "MSFT": 420.10,
                "GOOG": 175.25,
            }}

            def {tool_name}_handler(args, **kwargs):
                ticker = str(args.get("ticker", "")).upper().strip()
                if not ticker:
                    return tool_error("ticker is required")
                price = _MOCK_PRICES.get(ticker)
                if price is None:
                    return tool_error(f"No mock price for {{ticker}}")
                return tool_result(success=True, ticker=ticker, price=price, currency="USD")

            registry.register(
                name="{tool_name}",
                toolset="generated",
                schema={{
                    "name": "{tool_name}",
                    "description": {description!r},
                    "parameters": {{
                        "type": "object",
                        "properties": {{
                            "ticker": {{"type": "string", "description": "Stock ticker symbol"}},
                        }},
                        "required": ["ticker"],
                    }},
                }},
                handler={tool_name}_handler,
                emoji="🧬",
            )
            '''
        ).strip() + "\n"

    def _render_track_time_tool_code(self, tool_name: str, description: str, *, rewrite_hint: str | None = None) -> str:
        hint = f"\n# Rewrite note: {rewrite_hint}\n" if rewrite_hint else ""
        return textwrap.dedent(
            f'''
            """Generated tool: {tool_name}"""
            {hint}
            from tools.registry import registry, tool_result, tool_error

            _ACTIVE: dict[str, float] = {{}}

            def {tool_name}_handler(args, **kwargs):
                project = str(args.get("project", "")).strip()
                if not project:
                    return tool_error("project is required")
                action = str(args.get("action", "log")).strip().lower()
                minutes = args.get("minutes")
                if action == "start":
                    import time
                    _ACTIVE[project] = time.time()
                    return tool_result(success=True, project=project, action="start", status="running")
                if action == "stop":
                    import time
                    started = _ACTIVE.pop(project, None)
                    if started is None:
                        return tool_error(f"No active timer for {{project}}")
                    elapsed_minutes = round((time.time() - started) / 60.0, 2)
                    return tool_result(
                        success=True,
                        project=project,
                        action="stop",
                        minutes=elapsed_minutes,
                    )
                if minutes is None:
                    return tool_error("minutes is required when action is log")
                try:
                    logged_minutes = float(minutes)
                except (TypeError, ValueError):
                    return tool_error("minutes must be a number")
                return tool_result(
                    success=True,
                    project=project,
                    action="log",
                    minutes=logged_minutes,
                )

            registry.register(
                name="{tool_name}",
                toolset="generated",
                schema={{
                    "name": "{tool_name}",
                    "description": {description!r},
                    "parameters": {{
                        "type": "object",
                        "properties": {{
                            "project": {{"type": "string", "description": "Project label"}},
                            "action": {{
                                "type": "string",
                                "enum": ["start", "stop", "log"],
                                "description": "Timer action",
                            }},
                            "minutes": {{"type": "number", "description": "Duration to log when action is log"}},
                        }},
                        "required": ["project"],
                    }},
                }},
                handler={tool_name}_handler,
                emoji="🧬",
            )
            '''
        ).strip() + "\n"

    def _render_track_time_skill_yaml(self, tool_name: str, description: str) -> str:
        return (
            f"name: {tool_name}\n"
            f"description: {description}\n"
            "triggers:\n"
            '  - "track my time"\n'
            '  - "time tracking"\n'
            '  - "start timer"\n'
            "tools:\n"
            f"  - {tool_name}\n"
        )

    def _render_generic_tool_code(
        self,
        tool_name: str,
        description: str,
        task: str,
        *,
        rewrite_hint: str | None = None,
    ) -> str:
        hint = f"\n# Rewrite note: {rewrite_hint}\n" if rewrite_hint else ""
        query_key = "query" if "query" in task.lower() else "input"
        return textwrap.dedent(
            f'''
            """Generated tool: {tool_name}"""
            {hint}
            from tools.registry import registry, tool_result, tool_error

            def {tool_name}_handler(args, **kwargs):
                value = str(args.get("{query_key}", "")).strip()
                if not value:
                    return tool_error("{query_key} is required")
                return tool_result(success=True, {query_key}=value, summary={description!r})

            registry.register(
                name="{tool_name}",
                toolset="generated",
                schema={{
                    "name": "{tool_name}",
                    "description": {description!r},
                    "parameters": {{
                        "type": "object",
                        "properties": {{
                            "{query_key}": {{"type": "string", "description": "Primary input for {tool_name}"}},
                        }},
                        "required": ["{query_key}"],
                    }},
                }},
                handler={tool_name}_handler,
                emoji="🧬",
            )
            '''
        ).strip() + "\n"

    def _render_stock_skill_yaml(self, tool_name: str, description: str) -> str:
        return (
            f"name: {tool_name}\n"
            f"description: {description}\n"
            "triggers:\n"
            '  - "stock price"\n'
            '  - "what is {ticker} trading at"\n'
            '  - "current price of {ticker}"\n'
            "tools:\n"
            f"  - {tool_name}\n"
        )

    def _render_generic_skill_yaml(self, tool_name: str, description: str, task: str) -> str:
        snippet = task.strip()[:60] or tool_name
        return (
            f"name: {tool_name}\n"
            f"description: {description}\n"
            "triggers:\n"
            f'  - "{snippet}"\n'
            f'  - "use {tool_name}"\n'
            "tools:\n"
            f"  - {tool_name}\n"
        )


def _normalize_tool_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
    if not cleaned:
        return "generated_tool"
    if cleaned[0].isdigit():
        cleaned = f"tool_{cleaned}"
    return cleaned[:64]


def _is_stock_gap(task: str, tool_name: str, description: str) -> bool:
    blob = f"{task} {tool_name} {description}".lower()
    return "stock" in blob or "ticker" in blob or tool_name == "fetch_stock_price"


def _is_time_tracking_gap(task: str, tool_name: str, candidate_tool_name: str) -> bool:
    blob = f"{task} {tool_name} {candidate_tool_name}".lower()
    return tool_name == "track_time" or candidate_tool_name == "track_time" or (
        "time" in blob and ("track" in blob or "timer" in blob or "timesheet" in blob)
    )


def _default_test_input(tool_name: str, task: str) -> dict[str, Any]:
    lowered = f"{tool_name} {task}".lower()
    if "email" in lowered:
        return {"to": "user@example.com", "subject": "Test", "body": "Hello"}
    if "calendar" in lowered or "meeting" in lowered:
        return {"title": "Standup", "start": "2026-01-01T09:00:00Z"}
    if "database" in lowered or "sql" in lowered:
        return {"query": "SELECT 1"}
    if "track_time" in lowered or "time track" in lowered:
        return {"project": "demo project", "action": "start"}
    return {"input": task[:120] or "test"}


def _extract_json_payload(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    stripped = _FENCE_RE.sub("", raw.strip())
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None
    candidate = stripped[first : last + 1]
    try:
        value = json.loads(candidate)
    except (ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _build_result_from_payload(payload: dict[str, Any], *, tool_name: str, description: str) -> SynthesisResult:
    tool_code = str(payload.get("tool_code") or "").strip()
    skill_yaml = str(payload.get("skill_yaml") or "").strip()
    test_input = payload.get("test_input")

    if not tool_code or not skill_yaml:
        raise SynthesisError("LLM payload missing tool_code or skill_yaml")
    if not isinstance(test_input, dict) or not test_input:
        raise SynthesisError("LLM payload missing test_input dict")

    try:
        ast.parse(tool_code)
    except SyntaxError as exc:
        raise SynthesisError(f"Generated tool_code has syntax error: {exc}") from exc

    if "registry.register" not in tool_code:
        raise SynthesisError("Generated tool_code does not call registry.register")
    if f'name="{tool_name}"' not in tool_code and f"name='{tool_name}'" not in tool_code:
        tool_code = _ensure_tool_name(tool_code, tool_name)

    if f"name: {tool_name}" not in skill_yaml:
        skill_yaml = f"name: {tool_name}\n{skill_yaml}"

    return SynthesisResult(
        tool_name=tool_name,
        tool_code=tool_code if tool_code.endswith("\n") else tool_code + "\n",
        skill_yaml=skill_yaml if skill_yaml.endswith("\n") else skill_yaml + "\n",
        description=description,
        test_input=test_input,
    )


def _ensure_tool_name(tool_code: str, tool_name: str) -> str:
    replaced = re.sub(
        r'name\s*=\s*["\'][a-zA-Z0-9_]+["\']',
        f'name="{tool_name}"',
        tool_code,
        count=1,
    )
    return replaced

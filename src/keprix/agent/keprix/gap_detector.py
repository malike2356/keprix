"""Detect capability gaps before tool dispatch."""

from __future__ import annotations

import logging
import re

from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.gap_classifier_prompt import (
    build_gap_classifier_messages,
    parse_gap_classifier_response,
)
from keprix.agent.keprix.schemas import GapReport

logger = logging.getLogger(__name__)


class GapDetector:
    def classify(self, task: str, available_tools: list[str]) -> GapReport:
        """Sync fast-path classification (regex demos). LLM path uses classify_async."""
        config = get_mutation_config()
        if not config.enabled:
            return GapReport(has_gap=False, task=task)

        tool_names = {name.lower() for name in available_tools}
        report = self._fast_path_report(task, tool_names)
        if report is not None:
            return report
        return GapReport(has_gap=False, task=task)

    async def classify_async(self, task: str, available_tools: list[str]) -> GapReport:
        config = get_mutation_config()
        if not config.enabled:
            return GapReport(has_gap=False, task=task)

        tool_names = {name.lower() for name in available_tools}
        report = self._fast_path_report(task, tool_names)
        if report is not None:
            return report

        llm_report = await self._llm_classify_async(task, available_tools)
        if llm_report.has_gap and llm_report.confidence >= config.gap_confidence:
            return llm_report
        return GapReport(has_gap=False, task=task, confidence=llm_report.confidence)

    def _fast_path_report(self, task: str, tool_names: set[str]) -> GapReport | None:
        lowered = task.lower()
        if self._stock_price_gap(lowered, tool_names):
            return GapReport(
                has_gap=True,
                gap_description="No tool exists to fetch live stock prices.",
                candidate_tool_name="fetch_stock_price",
                candidate_approach="Use a public market data API or yfinance-style lookup.",
                confidence=0.92,
                task=task,
            )
        if self._time_tracking_gap(lowered, tool_names):
            return GapReport(
                has_gap=True,
                gap_description="No tool exists to track time on projects.",
                candidate_tool_name="track_time",
                candidate_approach="Store time entries with project label, start/stop or duration input.",
                confidence=0.88,
                task=task,
            )
        return None

    def _stock_price_gap(self, task: str, tool_names: set[str]) -> bool:
        if "fetch_stock_price" in tool_names or "stock_price" in tool_names:
            return False
        return bool(re.search(r"\b(stock price|trading at|share price|ticker)\b", task)) or (
            "aapl" in task or "apple" in task and "price" in task
        )

    def _time_tracking_gap(self, task: str, tool_names: set[str]) -> bool:
        if any(name in tool_names for name in ("track_time", "time_tracker", "timesheet")):
            return False
        return bool(
            re.search(
                r"\b(track(?:ing)?\s+(?:my\s+)?time|time\s+track|timesheet|timer)\b",
                task,
            )
        )

    async def _llm_classify_async(self, task: str, available_tools: list[str]) -> GapReport:
        from agent.auxiliary_client import async_call_llm, extract_content_or_reasoning

        messages = build_gap_classifier_messages(task, available_tools)
        try:
            response = await async_call_llm(
                task="mutation_gap_classify",
                messages=messages,
                temperature=0.0,
                max_tokens=800,
            )
        except Exception as exc:
            logger.warning("LLM gap classification unavailable: %s", exc)
            return GapReport(has_gap=False, task=task, confidence=0.0)

        raw = extract_content_or_reasoning(response).strip()
        if not raw:
            return GapReport(has_gap=False, task=task, confidence=0.0)

        parsed = parse_gap_classifier_response(raw, task=task)
        if not parsed.get("has_gap"):
            return GapReport(has_gap=False, task=task, confidence=float(parsed.get("confidence") or 0.0))

        return GapReport(
            has_gap=True,
            gap_description=str(parsed.get("gap_description") or "No matching tool for this task."),
            candidate_tool_name=str(parsed.get("candidate_tool_name") or "generated_tool"),
            candidate_approach=str(parsed.get("candidate_approach") or "Synthesise a focused tool for this task."),
            confidence=float(parsed.get("confidence") or 0.0),
            task=task,
        )

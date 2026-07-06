"""Local browser task benchmarks."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.browser.drivers import StubBrowserDriver
from keprix.browser.harness import BrowserHarness, get_harness_manager


@dataclass
class BenchmarkResult:
    benchmark_id: str
    name: str
    success: bool
    failure_reason: str | None
    trace_id: str
    screenshot_ids: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BUILTIN_BENCHMARKS: dict[str, str] = {
    "form_fill": "Fill search and email fields without submit",
    "search_compare": "Search and read comparison results",
    "login_navigate": "Navigate to login page and read form",
    "extract_table": "Read page and extract visible table rows",
    "download_file": "Attempt report download (approval gated)",
    "fill_no_submit": "Fill checkout form without submitting",
}


class BrowserBenchmarkRunner:
    def __init__(self) -> None:
        self._results: dict[str, BenchmarkResult] = {}

    def list_benchmarks(self) -> list[dict[str, str]]:
        return [{"id": key, "description": value} for key, value in BUILTIN_BENCHMARKS.items()]

    def run(self, benchmark_id: str, *, workspace_id: str = "default") -> BenchmarkResult:
        if benchmark_id not in BUILTIN_BENCHMARKS:
            raise KeyError(benchmark_id)
        trace_id = str(uuid.uuid4())
        harness, record = get_harness_manager().open_session(
            workspace_id=workspace_id,
            objective=BUILTIN_BENCHMARKS[benchmark_id],
            url="https://example.com",
            driver=StubBrowserDriver(),
        )
        trace_id = record.trace_id
        screenshot_ids: list[str] = []
        failure_reason: str | None = None
        success = True
        try:
            if benchmark_id == "form_fill":
                harness.engine.run_action(harness.session_id, action="fill", selector="search", value="widget")
                harness.engine.run_action(harness.session_id, action="fill", selector="email", value="a@b.com")
            elif benchmark_id == "search_compare":
                harness.engine.run_action(harness.session_id, action="fill", selector="search", value="pricing")
                harness.engine.run_action(harness.session_id, action="read_page")
            elif benchmark_id == "login_navigate":
                harness.navigate("https://example.com/login")
            elif benchmark_id == "extract_table":
                snap = harness.capture()
                if "Stub browser" not in snap.dom_snapshot and not snap.accessibility_tree:
                    success = False
                    failure_reason = "No visible elements to extract"
            elif benchmark_id == "download_file":
                result = harness.engine.run_action(harness.session_id, action="download_sensitive", selector="report")
                success = result.get("status") == "awaiting_approval"
                if not success:
                    failure_reason = "Expected approval gate for download"
            elif benchmark_id == "fill_no_submit":
                harness.engine.run_action(harness.session_id, action="fill", selector="card", value="4111111111111111")
                pending = harness.engine.run_action(harness.session_id, action="submit", selector="checkout")
                success = pending.get("status") == "awaiting_approval"
                if not success:
                    failure_reason = "Submit should require approval"
            snap = harness.capture()
            if snap.screenshot_id:
                screenshot_ids.append(snap.screenshot_id)
        except Exception as exc:
            success = False
            failure_reason = str(exc)
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            name=benchmark_id,
            success=success,
            failure_reason=failure_reason,
            trace_id=trace_id,
            screenshot_ids=screenshot_ids,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        self._results[trace_id] = result
        return result

    def get_result(self, trace_id: str) -> BenchmarkResult | None:
        return self._results.get(trace_id)


_runner: BrowserBenchmarkRunner | None = None


def get_benchmark_runner() -> BrowserBenchmarkRunner:
    global _runner
    if _runner is None:
        _runner = BrowserBenchmarkRunner()
    return _runner

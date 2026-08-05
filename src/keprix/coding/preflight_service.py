"""Coding preflight service and ledger hook."""

from __future__ import annotations

from typing import Any

from keprix.coding.gates.diff_budget import run_diff_budget_gate
from keprix.coding.gates.duplicate_task import run_duplicate_task_gate
from keprix.coding.gates.provider_budget import run_provider_budget_gate
from keprix.coding.gates.repo_index import run_repo_index_gate
from keprix.coding.gates.test_exists import run_test_exists_gate
from keprix.coding.preflight_config import PreflightConfig, get_preflight_config
from keprix.coding.preflight_store import PreflightGateResult, PreflightReport, PreflightStore


class PreflightService:
    def __init__(self, *, store: PreflightStore | None = None, config: PreflightConfig | None = None) -> None:
        self.store = store or PreflightStore()
        self.config = config or get_preflight_config()

    def run(self, *, session_id: str, payload: dict[str, Any]) -> PreflightReport:
        if not self.config.enabled:
            report = PreflightReport(
                session_id=session_id,
                results=[PreflightGateResult("preflight", "pass", "Coding preflight is disabled.", {})],
                overall="proceed",
                tokens_saved_estimate=0,
            )
            return self.store.save(report)
        results: list[PreflightGateResult] = []
        if self.config.gates.get("repo_index", True):
            results.append(run_repo_index_gate(payload))
        if self.config.gates.get("duplicate_task", True):
            results.append(run_duplicate_task_gate(payload, window_turns=self.config.duplicate_window_turns))
        if self.config.gates.get("test_exists", True):
            results.append(run_test_exists_gate(payload))
        if self.config.gates.get("diff_budget", True):
            results.append(run_diff_budget_gate(payload, limit=self.config.diff_budget_lines))
        if self.config.gates.get("provider_budget", True):
            results.append(run_provider_budget_gate(payload, warn_pct=self.config.provider_budget_warn_pct))
        report = PreflightReport(
            session_id=session_id,
            results=results,
            overall=self._overall(results),
            tokens_saved_estimate=self._tokens_saved(results),
        )
        self.store.save(report)
        self._record_ledger(report)
        return report

    def override(self, session_id: str) -> PreflightReport | None:
        if not self.config.allow_override:
            return self.store.get(session_id)
        return self.store.override(session_id)

    def _overall(self, results: list[PreflightGateResult]) -> str:
        if any(result.status == "block" for result in results):
            return "block"
        if any(result.status == "warn" for result in results):
            return "warn"
        return "proceed"

    def _tokens_saved(self, results: list[PreflightGateResult]) -> int:
        estimate = 0
        for result in results:
            if result.status == "warn":
                estimate += 400
            elif result.status == "block":
                planned = int(result.metadata.get("planned_lines") or 0)
                estimate += max(1000, planned * 25)
        return estimate

    def _record_ledger(self, report: PreflightReport) -> None:
        if report.tokens_saved_estimate <= 0:
            return
        try:
            from keprix.agent_os.hooks import record_external_run

            record_external_run(
                source_type="coding_preflight",
                source_id=report.session_id,
                run_id=report.report_id,
                workspace_id="default",
                status=report.overall,
                output_summary={
                    "tokens_saved_estimate": report.tokens_saved_estimate,
                    "gates_triggered": [result.gate for result in report.results if result.status != "pass"],
                },
                tokens=0,
            )
        except Exception:
            pass

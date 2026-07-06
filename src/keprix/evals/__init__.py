"""Benchmark and quality regression harness."""

from keprix.evals.cost import detect_cost_regression
from keprix.evals.datasets import discover_suites, find_evals_root, load_all_into_registry, load_suite_file
from keprix.evals.latency import detect_latency_regression
from keprix.evals.provider_compare import ProviderScore, compare_providers
from keprix.evals.registry import EvalCategory, EvalRegistry, EvalSuite, EvalTask, eval_registry
from keprix.evals.reports import ReleaseGateResult, evaluate_release_gate, render_json_report, render_markdown_report
from keprix.evals.runner import EvalRunner, SuiteResult, TaskResult, get_runner
from keprix.evals.safety import SafetyCheckResult, evaluate_safety_task, is_safety_task, safety_pass_rate
from keprix.evals.scorers import score_task, score_tool_success, score_trajectory

__all__ = [
    "EvalCategory",
    "EvalRegistry",
    "EvalRunner",
    "EvalSuite",
    "EvalTask",
    "ProviderScore",
    "ReleaseGateResult",
    "SafetyCheckResult",
    "SuiteResult",
    "TaskResult",
    "compare_providers",
    "detect_cost_regression",
    "detect_latency_regression",
    "discover_suites",
    "evaluate_release_gate",
    "evaluate_safety_task",
    "find_evals_root",
    "get_runner",
    "is_safety_task",
    "load_all_into_registry",
    "load_suite_file",
    "eval_registry",
    "render_json_report",
    "render_markdown_report",
    "safety_pass_rate",
    "score_task",
    "score_tool_success",
    "score_trajectory",
]

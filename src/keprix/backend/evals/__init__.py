"""Backend eval harness (Prompt 57)."""

from keprix.backend.evals.benchmark import BenchmarkRunner, get_benchmark_runner
from keprix.backend.evals.datasets import load_all_benchmarks
from keprix.backend.evals.graders import GraderType, GradingContext, run_graders
from keprix.backend.evals.regression import compare_to_baseline, save_baseline
from keprix.backend.evals.reports import build_report
from keprix.backend.evals.trace import AgentRunTrace, redact_dict

__all__ = [
    "AgentRunTrace",
    "BenchmarkRunner",
    "GraderType",
    "GradingContext",
    "build_report",
    "compare_to_baseline",
    "get_benchmark_runner",
    "load_all_benchmarks",
    "redact_dict",
    "run_graders",
    "save_baseline",
]

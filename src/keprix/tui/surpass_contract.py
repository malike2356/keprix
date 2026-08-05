"""Keprix TUI surpass-Hermes proof contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SurpassStatus = Literal["passed", "partial", "missing", "different_by_design"]


@dataclass(frozen=True)
class TuiSurpassContractItem:
    id: str
    title: str
    why_it_surpasses: str
    implementation: str
    test: str
    benchmark_or_contract: str
    status: SurpassStatus = "passed"
    required: bool = True


_ITEMS: tuple[TuiSurpassContractItem, ...] = (
    TuiSurpassContractItem(
        id="granularity.01",
        title="Granular package boundaries",
        why_it_surpasses="Keprix separates commands, renderer, runtime, terminal, panels, overlays, gateway, sessions, and search into tested subpackages while keeping compatibility imports.",
        implementation="src/keprix/tui/commands",
        test="tests/tui/test_granularity_contract.py",
        benchmark_or_contract="Required subpackages and compatibility imports",
    ),
    TuiSurpassContractItem(
        id="renderer.01",
        title="Pure renderer contracts above Textual",
        why_it_surpasses="Keprix keeps Textual integration but adds pure cells, measurement, diff, markdown, viewport, selection, snapshot, and benchmark contracts that can be tested without widgets.",
        implementation="src/keprix/tui/renderer",
        test="tests/tui/test_renderer_contracts.py",
        benchmark_or_contract="tests/tui/test_renderer_benchmarks.py",
    ),
    TuiSurpassContractItem(
        id="runtime_transport.01",
        title="One runtime interface across transport modes",
        why_it_surpasses="Keprix supports HTTP, WebSocket, and safe in-process transports through one typed interface, so runtime proximity can improve without collapsing boundaries.",
        implementation="src/keprix/tui/runtime_transport",
        test="tests/tui/test_runtime_transport_contract.py",
        benchmark_or_contract="tests/tui/test_runtime_event_normalization.py",
    ),
    TuiSurpassContractItem(
        id="performance.01",
        title="Local latency and memory budgets",
        why_it_surpasses="Keprix proves slash picker, transcript viewport, interrupt scheduling, resize handling, render benchmark, and memory caps with local tests.",
        implementation="src/keprix/tui/hardening.py",
        test="tests/tui/test_performance_budgets.py",
        benchmark_or_contract="tests/tui/test_memory_budgets.py",
    ),
    TuiSurpassContractItem(
        id="reliability.01",
        title="Explicit fault matrix",
        why_it_surpasses="Keprix has local tests for common backend errors, invalid stream lines, missing runtime ids, offline registries, and no traceback user copy.",
        implementation="src/keprix/tui/hardening.py",
        test="tests/tui/test_fault_matrix.py",
        benchmark_or_contract="tests/tui/test_overlay_recovery.py",
    ),
    TuiSurpassContractItem(
        id="terminal_matrix.01",
        title="Terminal degradation matrix",
        why_it_surpasses="Keprix validates xterm, tmux, screen, iTerm2, WezTerm, Kitty, Windows Terminal, VS Code, Termux, and dumb-terminal detection.",
        implementation="src/keprix/tui/terminal_capabilities.py",
        test="tests/tui/test_terminal_matrix.py",
        benchmark_or_contract="tests/tui/test_terminal_capabilities.py",
    ),
    TuiSurpassContractItem(
        id="developer_experience.01",
        title="Repeatable proof script",
        why_it_surpasses="Keprix provides a single script that runs parity, surpass contracts, granularity, renderer, runtime, performance, fault, and terminal checks.",
        implementation="scripts/check-tui-surpass-hermes.sh",
        test="tests/tui/test_tui_surpass_contract.py",
        benchmark_or_contract="scripts/check-tui-parity.sh",
    ),
    TuiSurpassContractItem(
        id="command_center.01",
        title="Agent OS command center",
        why_it_surpasses="Keprix adds command palette, cockpit, runtime timeline, tool cards, session map, themes, status bar, review mode, state views, and a tested keyboard model as one operator workflow.",
        implementation="src/keprix/tui/command_center",
        test="tests/tui/test_command_center_final_contract.py",
        benchmark_or_contract="tests/tui/test_command_center_surpass_proof.py",
    ),
    TuiSurpassContractItem(
        id="look_and_feel_boundary.01",
        title="Keprix visual identity remains different by design",
        why_it_surpasses="Keprix adopts behavior and proof discipline without copying Hermes surface styling, copy, or visual identity.",
        implementation="docs/architecture/tui-surpass-hermes-contract.md",
        test="tests/tui/test_tui_surpass_contract.py",
        benchmark_or_contract="Keprix look and feel boundary",
        status="different_by_design",
        required=False,
    ),
)


def tui_surpass_contract() -> list[TuiSurpassContractItem]:
    return list(_ITEMS)


def required_surpass_failures() -> list[TuiSurpassContractItem]:
    return [item for item in _ITEMS if item.required and item.status in {"partial", "missing"}]


def surpass_summary() -> str:
    failures = required_surpass_failures()
    if failures:
        return "TUI surpass contracts: failed"
    return "TUI surpass contracts: passed"


__all__ = [
    "TuiSurpassContractItem",
    "required_surpass_failures",
    "surpass_summary",
    "tui_surpass_contract",
]

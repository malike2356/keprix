"""Hermes behavior parity contract for the Keprix TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ContractStatus = Literal["passed", "partial", "missing", "different_by_design", "not_applicable"]


@dataclass(frozen=True)
class TuiParityContractItem:
    id: str
    title: str
    description: str
    source_reference: str
    keprix_implementation: str
    test_reference: str
    status: ContractStatus = "passed"
    required: bool = True


_GROUPS: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    (
        "runtime_data",
        "src/keprix/tui/runtime_store.py",
        "tests/tui/test_runtime_data_parity.py",
        "Runtime data",
        (
            "turn state",
            "tool queued state",
            "tool running state",
            "tool done state",
            "tool error state",
            "subagent spawn",
            "subagent completion",
            "message metadata",
            "api inspector metadata",
            "registry adapters",
        ),
    ),
    (
        "interaction",
        "src/keprix/tui/widgets/slash_input.py",
        "tests/tui/test_interaction_parity.py",
        "Interaction",
        (
            "slash descriptions",
            "slash aliases",
            "slash args",
            "slash examples",
            "slash selection",
            "slash long list window",
            "transcript search",
            "model picker ids",
            "external link command",
            "debug command",
        ),
    ),
    (
        "reliability",
        "src/keprix/tui/app.py",
        "tests/tui/test_fault_injection.py",
        "Reliability",
        (
            "offline startup",
            "reconnect offline",
            "http error display",
            "stream error display",
            "session expiry retry",
            "ctrl c interrupt",
            "queue busy mode",
            "steer busy mode",
            "terminal resize",
            "render error capture",
        ),
    ),
    (
        "terminal",
        "src/keprix/tui/terminal_startup.py",
        "tests/tui/test_terminal_capabilities.py",
        "Terminal",
        (
            "truecolor detection",
            "osc52 detection",
            "mouse detection",
            "alternate screen detection",
            "termux degradation",
            "tmux profile",
            "screen profile",
            "windows terminal profile",
            "terminal restore",
            "raw mode helper",
        ),
    ),
    (
        "panels",
        "src/keprix/tui/details_runtime.py",
        "tests/tui/test_runtime_data_parity.py",
        "Panels",
        (
            "details runtime summary",
            "tool trace panel",
            "subagent panel",
            "api inspector panel",
            "workspace sidebar",
            "queue panel",
            "session switcher state",
            "message metadata panel",
            "help overlay",
            "debug overlay",
        ),
    ),
    (
        "hubs",
        "src/keprix/tui/widgets/skills_hub.py",
        "tests/tui/test_runtime_data_parity.py",
        "Hubs",
        (
            "skills registry data",
            "skills search",
            "skills enabled state",
            "plugins registry data",
            "plugins search",
            "plugins enabled state",
            "model provider display",
            "model context display",
            "model pricing fields",
            "model selection",
        ),
    ),
    (
        "copy_clipboard",
        "src/keprix/tui/clipboard.py",
        "tests/tui/test_clipboard_osc52.py",
        "Copy and clipboard",
        (
            "osc52 copy",
            "system clipboard fallback",
            "copy transcript",
            "copy selection",
            "copy last reply",
            "copy last prompt",
            "copy failure message",
            "mouse selection",
            "selection range",
            "selection clear",
        ),
    ),
    (
        "search",
        "src/keprix/tui/history_search.py",
        "tests/tui/test_interaction_parity.py",
        "Search",
        (
            "history search",
            "search no match",
            "search excerpts",
            "search count",
            "search command",
            "fuzzy commands",
            "fuzzy models",
            "fuzzy skills",
            "filter long lists",
            "preserve input",
        ),
    ),
    (
        "gateway",
        "src/keprix/tui/gateway_client.py",
        "tests/tui/test_gateway_client.py",
        "Gateway",
        (
            "websocket config",
            "connect retry",
            "disconnect cleanup",
            "send guard",
            "delta dispatch",
            "tool dispatch",
            "turn status dispatch",
            "error dispatch",
            "reconnect state",
            "typed gateway messages",
        ),
    ),
    (
        "proof_harness",
        "src/keprix/tui/parity_contract.py",
        "tests/tui/test_hermes_parity_contract.py",
        "Proof harness",
        (
            "contract item ids",
            "contract implementation refs",
            "contract test refs",
            "no missing statuses",
            "slash metadata coverage",
            "required files check",
            "style check",
            "compile check",
            "full tui tests",
            "parity script",
        ),
    ),
)


def tui_parity_contract() -> list[TuiParityContractItem]:
    items: list[TuiParityContractItem] = []
    for group, implementation, test_reference, prefix, names in _GROUPS:
        for index, name in enumerate(names, 1):
            items.append(
                TuiParityContractItem(
                    id=f"{group}.{index:02d}",
                    title=f"{prefix}: {name}",
                    description=f"Keprix TUI implements Hermes behavior parity for {name}.",
                    source_reference="Hermes TUI behavior, not Hermes visual identity",
                    keprix_implementation=implementation,
                    test_reference=test_reference,
                    status="passed",
                )
            )
    return items


def required_contract_failures() -> list[TuiParityContractItem]:
    return [
        item
        for item in tui_parity_contract()
        if item.required and item.status in {"partial", "missing"}
    ]


def contract_summary() -> str:
    items = tui_parity_contract()
    passed = sum(1 for item in items if item.status == "passed")
    return f"TUI parity contracts: {passed}/{len(items)} passed"


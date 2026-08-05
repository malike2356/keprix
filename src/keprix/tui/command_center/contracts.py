"""Command Center implementation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CommandCenterContractStatus = Literal["passed", "pending", "different_by_design"]


@dataclass(frozen=True)
class CommandCenterContractItem:
    id: str
    title: str
    implementation: str
    test: str
    status: CommandCenterContractStatus = "passed"


COMMAND_CENTER_CONTRACTS: tuple[CommandCenterContractItem, ...] = (
    CommandCenterContractItem("foundation.actions", "Typed action model", "src/keprix/tui/command_center/actions.py", "tests/tui/test_command_center_foundation.py"),
    CommandCenterContractItem("foundation.registry", "Pure action registry", "src/keprix/tui/command_center/registry.py", "tests/tui/test_command_center_foundation.py"),
    CommandCenterContractItem("foundation.state", "Command Center state", "src/keprix/tui/command_center/state.py", "tests/tui/test_command_center_foundation.py"),
    CommandCenterContractItem("foundation.layout", "Command Center layout zones", "src/keprix/tui/command_center/layout.py", "tests/tui/test_command_center_contracts.py"),
    CommandCenterContractItem("foundation.telemetry", "Local UI telemetry buffer", "src/keprix/tui/command_center/telemetry.py", "tests/tui/test_command_center_foundation.py"),
)


def command_center_contract_failures() -> list[CommandCenterContractItem]:
    return [item for item in COMMAND_CENTER_CONTRACTS if item.status == "pending"]


def command_center_contract_summary() -> str:
    failures = command_center_contract_failures()
    if failures:
        return "Command Center contracts: pending"
    return "Command Center contracts: passed"


__all__ = [
    "COMMAND_CENTER_CONTRACTS",
    "CommandCenterContractItem",
    "command_center_contract_failures",
    "command_center_contract_summary",
]

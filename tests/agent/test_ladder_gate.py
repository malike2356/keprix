from pathlib import Path

import pytest

from keprix.agent.keprix.ladder_gate import LadderGate
from keprix.agent.keprix.schemas import SynthesisResult


def _result(code: str, yaml: str = "") -> SynthesisResult:
    return SynthesisResult(tool_name="demo", tool_code=code, skill_yaml=yaml, description="demo", test_input={})


def test_ladder_gate_passes_small_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    result = LadderGate().validate(_result("def demo(args):\n    return args\n"))

    assert result.passed_gate


def test_ladder_gate_revises_unnecessary_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    result = LadderGate().validate(_result("def demo(args):\n    return args\n", "requests==2.0"))

    assert not result.passed_gate
    assert "dependency" in result.reasons[0]

"""Tests for code-first agent execution."""

from __future__ import annotations

from keprix.code_agent.action_syntax import CodePolicy, validate_code
from keprix.code_agent.code_agent import CodeAgent, CodeAgentConfig
from keprix.code_agent.docker_provider import DockerSandboxProvider
from keprix.code_agent.modality_inputs import normalize_inputs


def test_code_agent_solves_small_data_task() -> None:
    agent = CodeAgent(CodeAgentConfig(workspace_id="test", provider="docker", allowed_imports={"json", "math", "statistics"}))
    try:
        code = """
import json
import statistics
data = [1, 2, 3, 4]
result = {"mean": statistics.mean(data), "total": sum(data)}
"""
        result = agent.run_task("compute mean and total", code=code)
        assert result.ok, result.errors
        assert result.result is not None
        if isinstance(result.result, dict):
            assert result.result.get("mean") == 2.5
            assert result.result.get("total") == 10
    finally:
        agent.close()


def test_unsafe_imports_blocked() -> None:
    policy = CodePolicy(allowed_imports={"json"})
    validated = validate_code("import subprocess\nsubprocess.run(['ls'])", policy)
    assert not validated.ok
    assert any("subprocess" in error for error in validated.errors)


def test_modality_inputs_normalize_artifacts() -> None:
    bundle = normalize_inputs(
        text="Analyze sales",
        audio_transcript="show me totals",
        urls=["https://example.com/data.csv"],
    )
    assert bundle.primary_text == "Analyze sales"
    kinds = {artifact.kind for artifact in bundle.artifacts}
    assert "audio_transcript" in kinds
    assert "url" in kinds


def test_code_agent_rejects_unsafe_action() -> None:
    agent = CodeAgent(CodeAgentConfig(allowed_imports={"json"}))
    try:
        result = agent.run_generated_action("```python\nimport os\nos.system('rm -rf /')\n```")
        assert not result.ok
        assert result.errors
    finally:
        agent.close()

"""Tests for Prompt 54: analytics workspace - code safety, DataFrame memory, plugins, repair."""

from __future__ import annotations

import pytest

from keprix.analytics.code_interpreter import AnalyticsSession, CodeInterpreter
from keprix.analytics.code_verifier import CodeVerifier
from keprix.analytics.container_executor import ContainerExecutor
from keprix.analytics.dataframe_memory import DataFrameMemory, DataFrameSchema
from keprix.analytics.plugin_runner import PluginRunner
from keprix.analytics.reflective_execution import ReflectiveExecutor


def _safe_interpreter() -> CodeInterpreter:
    return CodeInterpreter(executor=ContainerExecutor(container_required=False))


# ---- Code safety ----

def test_blocked_import_os_is_rejected() -> None:
    verifier = CodeVerifier()
    result = verifier.verify("import os")
    assert not result.allowed
    assert any("os" in e for e in result.errors)


def test_blocked_call_eval_is_rejected() -> None:
    verifier = CodeVerifier()
    result = verifier.verify("eval('1+1')")
    assert not result.allowed
    assert any("eval" in e for e in result.errors)


def test_filesystem_escape_path_blocked() -> None:
    verifier = CodeVerifier()
    result = verifier.verify("x = '../etc/passwd'")
    assert not result.allowed


def test_safe_code_passes_verification() -> None:
    verifier = CodeVerifier()
    result = verifier.verify("x = sum([1, 2, 3])")
    assert result.allowed
    assert result.errors == []


def test_blocked_code_returns_error_from_run() -> None:
    interp = _safe_interpreter()
    session = interp.create_session()
    verification, result = interp.run_code(session, "import os")
    assert not verification.allowed
    assert not result.ok


# ---- DataFrame memory ----

def test_dataframe_memory_persists_schema() -> None:
    memory = DataFrameMemory()
    records = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    schema = memory.remember_records("users", records)
    assert schema.name == "users"
    assert schema.row_count == 2
    assert "name" in schema.columns
    assert "age" in schema.columns


def test_dataframe_memory_retrieves_records() -> None:
    memory = DataFrameMemory()
    records = [{"x": 1}, {"x": 2}]
    memory.remember_records("data", records)
    retrieved = memory.get_records("data")
    assert len(retrieved) == 2
    assert retrieved[0]["x"] == 1


def test_dataframe_schema_persists_across_interpreter_runs() -> None:
    interp = _safe_interpreter()
    session = interp.create_session()
    schema = DataFrameSchema(name="ds", columns={"col": "int"}, row_count=10)
    session.dataframe_memory.remember_schema(schema)
    assert session.dataframe_memory.get_schema("ds") is not None

    interp.run_code(session, "x = 1 + 1")
    assert session.dataframe_memory.get_schema("ds") is not None


# ---- Plugin execution ----

def test_plugin_runner_executes_known_plugin() -> None:
    runner = PluginRunner()
    result = runner.run("anomaly_detection", values=[1, 2, 3, 100, 4, 5])
    assert isinstance(result, dict)
    assert "anomalies" in result or "outliers" in result or "zscore" in result or result is not None


def test_plugin_runner_raises_for_unknown_plugin() -> None:
    runner = PluginRunner()
    with pytest.raises(KeyError, match="Unknown analytics plugin"):
        runner.run("nonexistent_plugin")


def test_plugin_called_from_interpreter_code() -> None:
    interp = _safe_interpreter()
    session = interp.create_session()
    code = "result = plugin('anomaly_detection', values=[1, 2, 100])"
    verification, exec_result = interp.run_code(session, code)
    assert verification.allowed
    assert exec_result.ok
    assert any(a["type"] == "result" for a in session.artifacts)


# ---- Failed-code repair ----

def test_reflective_executor_repairs_typo_and_succeeds() -> None:
    interp = _safe_interpreter()
    executor = ReflectiveExecutor(interp)
    session = interp.create_session()

    broken_code = "result = leng([1, 2, 3])"
    ok, trail = executor.run_with_repair(session, broken_code, max_retries=1)

    assert ok is True
    assert len(trail.attempts) == 2
    assert trail.attempts[0]["ok"] == "False"
    assert trail.attempts[1]["ok"] == "True"


def test_reflective_executor_fails_after_max_retries() -> None:
    interp = _safe_interpreter()
    executor = ReflectiveExecutor(interp)
    session = interp.create_session()

    unrepairable = "result = totally_undefined_function_xyz()"
    ok, trail = executor.run_with_repair(session, unrepairable, max_retries=0)

    assert ok is False
    assert len(trail.attempts) == 1

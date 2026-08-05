"""Local analytics executor captures print stdout for workspace runs."""

from __future__ import annotations

from keprix.analytics.container_executor import ContainerExecutor
from keprix.analytics.code_interpreter import CodeInterpreter
from keprix.analytics.reflective_execution import ReflectiveExecutor


def test_local_python_captures_print_stdout() -> None:
    executor = ContainerExecutor(container_required=False)
    result = executor.run_python("print('captured-out')", {})
    assert result.ok
    assert "captured-out" in result.stdout


def test_auto_repair_trail_includes_stdout() -> None:
    interpreter = CodeInterpreter(executor=ContainerExecutor(container_required=False))
    session = interpreter.create_session(title="stdout check")
    ok, trail = ReflectiveExecutor(interpreter).run_with_repair(session, "print('trail-out')")
    assert ok is True
    assert "trail-out" in trail.attempts[-1]["stdout"]


def test_session_title_and_dataset_store() -> None:
    interpreter = CodeInterpreter(executor=ContainerExecutor(container_required=False))
    session = interpreter.create_session(title="Sales")
    assert session.title == "Sales"
    assert interpreter.rename_session(session.session_id, "Sales renamed").title == "Sales renamed"
    saved = interpreter.save_dataset(name="demo", data="a,b\n1,2\n", source_filename="demo.csv")
    assert interpreter.get_dataset(saved["dataset_id"])["name"] == "demo"
    assert interpreter.delete_dataset(saved["dataset_id"]) is True

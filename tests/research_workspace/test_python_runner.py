"""Python runner tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from keprix.research_workspace.notebooks.errors import DangerousCodeError, RunnerNotInstalledError
from keprix.research_workspace.notebooks.kernel_manager import detect_python
from keprix.research_workspace.notebooks.python_runner import run_python_script
from keprix.research_workspace.notebooks.sandbox import SandboxConfig, assert_code_allowed, redact_secrets, repair_suggestions


def test_detect_python_reports_optional_packages():
    detection = detect_python()
    assert detection.installed is True
    assert detection.binary


def test_dangerous_code_blocked():
    with pytest.raises(DangerousCodeError):
        assert_code_allowed("import subprocess\nsubprocess.run(['ls'])", SandboxConfig())


def test_secret_redaction():
    text = 'api_key = "sk-abcdefghijklmnopqrstuvwxyz123456"'
    assert "[redacted-secret]" in redact_secrets(text)


def test_repair_suggestions_for_missing_module():
    suggestions = repair_suggestions("ModuleNotFoundError: No module named pandas", 1)
    assert suggestions
    assert "pandas" in suggestions[0].lower() or "package" in suggestions[0].lower()


def test_run_python_fixture_script(tmp_path):
    workdir = tmp_path / "run"
    workdir.mkdir()
    script = workdir / "analysis.py"
    script.write_text("print('hello-keprix')\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = "hello-keprix\n"
        stderr = ""

    with patch("keprix.research_workspace.notebooks.python_runner.detect_python") as detect:
        detect.return_value.installed = True
        detect.return_value.binary = "/usr/bin/python3"
        detect.return_value.optional_packages = []
        with patch("keprix.research_workspace.notebooks.python_runner.subprocess.run", return_value=Completed()):
            result = run_python_script(workdir=workdir, script_path=script, config=SandboxConfig())
    assert result.return_code == 0
    assert "hello-keprix" in result.stdout
    assert Path(result.log_path).exists()


def test_run_python_missing_binary(tmp_path):
    workdir = tmp_path / "run"
    workdir.mkdir()
    script = workdir / "analysis.py"
    script.write_text("print('x')\n", encoding="utf-8")
    with patch("keprix.research_workspace.notebooks.python_runner.detect_python") as detect:
        detect.return_value.installed = False
        detect.return_value.setup_instructions = "install python"
        with pytest.raises(RunnerNotInstalledError):
            run_python_script(workdir=workdir, script_path=script, config=SandboxConfig())

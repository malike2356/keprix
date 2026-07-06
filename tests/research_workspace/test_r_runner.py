"""R runner tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from keprix.research_workspace.notebooks.errors import RunnerNotInstalledError
from keprix.research_workspace.notebooks.kernel_manager import detect_r
from keprix.research_workspace.notebooks.r_runner import run_r_script
from keprix.research_workspace.notebooks.sandbox import SandboxConfig


def test_detect_r_reports_setup_instructions():
    detection = detect_r()
    assert detection.setup_instructions


def test_run_r_fixture_script(tmp_path):
    workdir = tmp_path / "run"
    workdir.mkdir()
    script = workdir / "analysis.R"
    script.write_text("cat('hello-r\\n')\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = "hello-r\n"
        stderr = ""

    with patch("keprix.research_workspace.notebooks.r_runner.detect_r") as detect:
        detect.return_value.installed = True
        detect.return_value.binary = "/usr/bin/Rscript"
        detect.return_value.optional_packages = []
        with patch("keprix.research_workspace.notebooks.r_runner.subprocess.run", return_value=Completed()):
            result = run_r_script(workdir=workdir, script_path=script, config=SandboxConfig())
    assert result.return_code == 0
    assert "hello-r" in result.stdout
    assert Path(result.log_path).exists()


def test_run_r_missing_binary(tmp_path):
    workdir = tmp_path / "run"
    workdir.mkdir()
    script = workdir / "analysis.R"
    script.write_text("cat('x')\n", encoding="utf-8")
    with patch("keprix.research_workspace.notebooks.r_runner.detect_r") as detect:
        detect.return_value.installed = False
        detect.return_value.setup_instructions = "install R"
        with pytest.raises(RunnerNotInstalledError):
            run_r_script(workdir=workdir, script_path=script, config=SandboxConfig())

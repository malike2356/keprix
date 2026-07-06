"""Tests for FORGE deploy module."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.personas.forge.deploy import DeployResult, ForgeDeployPipeline


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_demo.py").write_text("def test_ok() -> None:\n    assert True\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def pipeline(python_project: Path) -> ForgeDeployPipeline:
    return ForgeDeployPipeline(project_root=python_project)


def test_detect_build_targets_python(pipeline: ForgeDeployPipeline) -> None:
    targets = pipeline.detect_build_targets()
    assert targets["python"] is True
    assert targets["test_command"] is not None


def test_run_tests_passes(pipeline: ForgeDeployPipeline, python_project: Path) -> None:
  # Use venv python if available via pytest in path
    result = pipeline.run_tests()
    assert result.stage == "test"


def test_run_build_returns_result(pipeline: ForgeDeployPipeline) -> None:
    result = pipeline.run_build()
    assert result.stage in {"lint", "build", "test"}


def test_generate_deploy_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pipeline = ForgeDeployPipeline(project_root=tmp_path)
    monkeypatch.setattr(pipeline, "run_build", lambda: DeployResult(ok=True, stage="build"))
    result = pipeline.run_deploy(target="local")
    assert result.ok
    assert result.stage == "deploy"
    assert "#!/usr/bin/env bash" in result.command


def test_deploy_script_includes_docker_steps(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM alpine\n", encoding="utf-8")
    pipeline = ForgeDeployPipeline(project_root=tmp_path)
    script = pipeline._generate_deploy_script("local")
    assert "docker build" in script
    assert "docker compose up" in script


def test_docker_project_detection(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\n", encoding="utf-8")
    pipeline = ForgeDeployPipeline(project_root=tmp_path)
    targets = pipeline.detect_build_targets()
    assert targets["docker"] is True
    assert "docker build" in (targets.get("build_command") or "")

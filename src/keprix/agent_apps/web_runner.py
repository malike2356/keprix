"""Web and API runners for agent apps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.agent_apps.runner_core import run_agent_app


def run_web(app_dir: Path, *, input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return run_agent_app(app_dir, input_text=input_text, context=context, runner="web")


def run_api(app_dir: Path, *, input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return run_agent_app(app_dir, input_text=input_text, context=context, runner="api")


def run_scheduled(app_dir: Path, *, input_text: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
    return run_agent_app(app_dir, input_text=input_text or "scheduled tick", context=context, runner="scheduled")

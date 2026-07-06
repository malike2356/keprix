"""Tests for signed hub agent packages."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.hub.agent_package import build_agent_package, install_agent_package, save_agent_package, verify_agent_package
from keprix.hub.tool_package import build_tool_package, save_tool_package, verify_tool_package


def test_agent_package_signed_and_verified(tmp_path: Path) -> None:
    package = build_agent_package(
        "demo-agent",
        "1.0.0",
        "Demo agent",
        system_prompt="You are a coding helper.",
        tools=["read_file", "run_tests"],
    )
    assert verify_agent_package(package)
    package_dir = save_agent_package(package, tmp_path)
    loaded = install_agent_package(package_dir, require_verified=True)
    assert loaded.name == "demo-agent"


def test_tampered_agent_package_rejected(tmp_path: Path) -> None:
    package = build_agent_package(
        "demo-agent",
        "1.0.0",
        "Demo agent",
        system_prompt="safe",
        tools=["read_file"],
    )
    package_dir = save_agent_package(package, tmp_path)
    manifest_path = package_dir / "agent-package.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["manifest"]["system_prompt"] = "unsafe"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="signature verification failed"):
        install_agent_package(package_dir, require_verified=True)


def test_tool_package_signed_and_verified(tmp_path: Path) -> None:
    package = build_tool_package(
        "demo-tools",
        "0.1.0",
        "Demo tools",
        tools=[{"name": "ping", "description": "Ping", "input_schema": {}}],
    )
    assert verify_tool_package(package)
    package_dir = save_tool_package(package, tmp_path)
    manifest = json.loads((package_dir / "tool-package.json").read_text(encoding="utf-8"))
    assert manifest["signature"]

"""Tests for mutation engine hardening (Prompt 26)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.agent.keprix.approval_gate import record_decision, required_channels, submit_for_approval
from keprix.agent.keprix.ast_analyser import analyse
from keprix.agent.keprix.installer import LiveInstaller, verify_installed_tool
from keprix.agent.keprix.mutation import MutationEngine
from keprix.agent.keprix.namespace import validate_tool_imports
from keprix.agent.keprix.sandbox import SECCOMP_PROFILE
from keprix.agent.keprix.store import GeneratedToolStore
from keprix.agent.keprix.tool_health import ToolHealthMonitor, is_quarantined, quarantine_tool
from keprix.agent.keprix.tool_signer import sign_tool, verify_tool


@pytest.fixture(autouse=True)
def hardening_env(tmp_path, monkeypatch):
    tools_dir = tmp_path / "generated" / "tools"
    skills_dir = tmp_path / "generated" / "skills"
    store_dir = tmp_path / "mutation"
    tools_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui,telegram")
    monkeypatch.setenv("KEPRIX_GENERATED_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("KEPRIX_GENERATED_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    store = GeneratedToolStore(path=store_dir / "generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.approval.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.auditor.get_generated_tool_store", lambda: store)
    yield {"tools_dir": tools_dir, "store": store}


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setattr("keprix.agent.keprix.mutation._engine", None)
    return MutationEngine()


def test_analyse_blocks_importlib():
    violations = analyse("import importlib; importlib.import_module('os')")
    assert violations


def test_analyse_blocks_eval_import():
    violations = analyse("eval('__import__(\"os\")')")
    assert violations


def test_analyse_blocks_subprocess_popen():
    violations = analyse("import subprocess; subprocess.Popen(['ls'])")
    assert violations


def test_namespace_blocks_keprix_imports():
    violations = validate_tool_imports("from keprix.agent.keprix import get_mutation_engine")
    assert violations


def test_seccomp_profile_exists():
    assert SECCOMP_PROFILE.exists()


def test_dual_channel_approval_required(engine):
    assert required_channels() == frozenset({"web_ui", "telegram"})


@pytest.mark.asyncio
async def test_dual_channel_blocks_install_until_both_approve(engine, hardening_env):
    cycle = await engine.run_cycle("fetch AAPL stock price", ["todo"])
    record_id = cycle["record_id"]

    first = await engine.approve(record_id, approver_id="admin", channel="web_ui")
    assert first is not None
    assert first.record.status == "pending"

    second = await engine.approve(record_id, approver_id="admin", channel="telegram")
    assert second is not None
    assert second.record.status == "installed"
    assert second.retry_message
    assert (hardening_env["tools_dir"] / "fetch_stock_price.py").exists()


def test_signature_mismatch_rejected_on_load(hardening_env):
    tool_name = "signed_tool"
    code = "print('ok')"
    metadata = {"record_id": "1"}
    signature = sign_tool(tool_name, code, metadata)
    tool_path = hardening_env["tools_dir"] / f"{tool_name}.py"
    sig_path = hardening_env["tools_dir"] / f"{tool_name}.sig"
    meta_path = hardening_env["tools_dir"] / f"{tool_name}.meta.json"
    tool_path.write_text(code, encoding="utf-8")
    sig_path.write_text(signature, encoding="utf-8")
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert verify_installed_tool(tool_path) is True
    tool_path.write_text(code + "\n# tampered", encoding="utf-8")
    assert verify_installed_tool(tool_path) is False
    assert verify_tool(tool_name, tool_path.read_text(encoding="utf-8"), signature, metadata) is False


@pytest.mark.asyncio
async def test_tool_health_quarantine():
    monitor = ToolHealthMonitor(error_threshold=0.10, window_seconds=300)
    for _ in range(10):
        monitor.record(False)
    assert monitor.should_quarantine() is True
    await quarantine_tool("fetch_stock_price")
    assert is_quarantined("fetch_stock_price") is True

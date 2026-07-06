"""Tests for the Keprix mutation engine (Prompt 28)."""

from __future__ import annotations

import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.agent.keprix.gap_detector import GapDetector
from keprix.agent.keprix.mutation import MutationEngine
from keprix.agent.keprix.static_analyser import static_analyser
from keprix.agent.keprix.store import GeneratedToolStore
from keprix.api.server import create_app


@pytest.fixture(autouse=True)
def mutation_env(tmp_path, monkeypatch):
    tools_dir = tmp_path / "generated" / "tools"
    skills_dir = tmp_path / "generated" / "skills"
    store_dir = tmp_path / "mutation"
    tools_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_GENERATED_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui")
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    store = GeneratedToolStore(path=store_dir / "generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.approval.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.auditor.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.routes.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.config.get_mutation_config", lambda: __import__("keprix.agent.keprix.config", fromlist=["get_mutation_config"]).get_mutation_config())
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.public_api.auth.effective_access_level", lambda: "developer")
    monkeypatch.setattr("keprix.agent.keprix.routes.effective_access_level", lambda: "developer")
    yield {"tools_dir": tools_dir, "store": store}


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setattr("keprix.agent.keprix.mutation._engine", None)
    return MutationEngine()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


def test_gap_detector_stock_price(engine):
    gap = engine.detect_gap("fetch AAPL stock price", ["todo", "web_search"])
    assert gap.has_gap is True
    assert gap.candidate_tool_name == "fetch_stock_price"


def test_gap_detector_disabled(monkeypatch):
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "false")
    from keprix.agent.keprix.config import get_mutation_config

    get_mutation_config.cache_clear() if hasattr(get_mutation_config, "cache_clear") else None
    gap = GapDetector().classify("fetch AAPL stock price", [])
    assert gap.has_gap is False


def test_static_analyser_blocks_eval():
    code = "result = eval('1+1')"
    analysis = static_analyser.scan(code)
    assert analysis.safe is False
    assert any("eval" in item for item in analysis.violations)


def test_static_analyser_blocks_subprocess_shell_true():
    code = "import subprocess\nsubprocess.run('ls', shell=True)"
    analysis = static_analyser.scan(code)
    assert analysis.safe is False


def test_static_analyser_blocks_recursive_mutation_import():
    code = "from keprix.agent.keprix import get_mutation_engine"
    analysis = static_analyser.scan(code)
    assert analysis.safe is False


@pytest.mark.asyncio
async def test_mutation_cycle_uses_llm_synthesis_when_available(engine, monkeypatch):
    captured: dict[str, str] = {}

    async def fake_async_call_llm(*_args, **kwargs):
        messages = kwargs.get("messages") or []
        captured["prompt"] = messages[-1]["content"]
        payload = {
            "tool_code": (
                '"""Generated tool: fetch_stock_price"""\n'
                "from tools.registry import registry, tool_result, tool_error\n"
                "_MOCK_PRICES = {'AAPL': 1.0}\n"
                "def fetch_stock_price_handler(args, **kwargs):\n"
                "    ticker = str(args.get('ticker', '')).upper().strip()\n"
                "    if not ticker:\n"
                "        return tool_error('ticker is required')\n"
                "    return tool_result(success=True, ticker=ticker, price=_MOCK_PRICES.get(ticker, 0))\n"
                "registry.register(name='fetch_stock_price', toolset='generated', schema={"
                "'name': 'fetch_stock_price', 'description': 'Fetch stock price', 'parameters': {"
                "'type': 'object', 'properties': {'ticker': {'type': 'string'}}, 'required': ['ticker']}}, "
                "handler=fetch_stock_price_handler, emoji='🧬')\n"
            ),
            "skill_yaml": "name: fetch_stock_price\ndescription: Fetch stock price\ntriggers:\n  - stock\n"
            "tools:\n  - fetch_stock_price\n",
            "test_input": {"ticker": "AAPL"},
        }
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_async_call_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    result = await engine.run_cycle("fetch AAPL stock price", ["todo"])
    assert result["started"] is True
    assert "fetch_stock_price" in captured.get("prompt", "")
    pending = engine.list_pending()
    assert pending[0].tool_code.startswith('"""Generated tool: fetch_stock_price"""')


@pytest.mark.asyncio
async def test_mutation_cycle_creates_pending_record(engine):
    result = await engine.run_cycle("fetch AAPL stock price", ["todo"])
    assert result["started"] is True
    assert result["tool_name"] == "fetch_stock_price"
    pending = engine.list_pending()
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_approve_installs_tool_and_retries(engine, mutation_env):
    cycle = await engine.run_cycle("fetch AAPL stock price", ["todo"])
    record_id = cycle["record_id"]
    installed = await engine.approve(record_id, approver_id="tester", channel="web_ui")
    assert installed is not None
    assert installed.record.status == "installed"
    tool_path = mutation_env["tools_dir"] / "fetch_stock_price.py"
    assert tool_path.exists()


@pytest.mark.asyncio
async def test_reject_keeps_audit_record(engine, mutation_env):
    cycle = await engine.run_cycle("fetch AAPL stock price", ["todo"])
    record_id = cycle["record_id"]
    rejected = await engine.reject(record_id, approver_id="tester", reason="no thanks")
    assert rejected is not None
    assert rejected.status == "rejected"
    record = mutation_env["store"].get(record_id)
    assert record is not None


@pytest.mark.asyncio
async def test_api_pending_and_approve(client, engine):
    cycle = await client.post(
        "/api/agent/tools/generated/cycle",
        json={"task": "fetch AAPL stock price", "available_tools": ["todo"]},
    )
    assert cycle.status_code == 200
    record_id = cycle.json()["record_id"]

    pending = await client.get("/api/agent/tools/generated/pending")
    assert pending.status_code == 200
    assert any(item["id"] == record_id for item in pending.json()["tools"])

    approved = await client.post(f"/api/agent/tools/generated/{record_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "installed"

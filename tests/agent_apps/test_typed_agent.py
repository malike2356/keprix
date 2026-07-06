"""
Tests for the TypedAgent DI framework (Pydantic AI gap closure, Prompt 66).

Covers: RunContext injection, Depends resolution, type validation,
sync/async tools, error handling, multi-tool runs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from keprix.agent_apps.dependencies import (
    AgentRun,
    Depends,
    DependencyError,
    RunContext,
    ToolResult,
    TypedAgent,
    _resolve_deps,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class SimpleDeps:
    db_url: str
    api_key: str


@dataclass
class EmptyDeps:
    pass


@dataclass
class LazyDeps:
    connection: str = field(default_factory=lambda: "not-set")


# ---------------------------------------------------------------------------
# RunContext
# ---------------------------------------------------------------------------


class TestRunContext:
    def test_fields_set_correctly(self):
        deps = SimpleDeps(db_url="postgres://localhost/test", api_key="key-123")
        ctx = RunContext(deps=deps, run_id="run-1", workspace_id="ws-1")
        assert ctx.deps.db_url == "postgres://localhost/test"
        assert ctx.deps.api_key == "key-123"
        assert ctx.run_id == "run-1"
        assert ctx.workspace_id == "ws-1"

    def test_optional_persona_defaults_to_none(self):
        ctx = RunContext(deps=EmptyDeps(), run_id="r", workspace_id="w")
        assert ctx.persona is None

    def test_metadata_defaults_to_empty_dict(self):
        ctx = RunContext(deps=EmptyDeps(), run_id="r", workspace_id="w")
        assert ctx.metadata == {}


# ---------------------------------------------------------------------------
# Depends
# ---------------------------------------------------------------------------


class TestDepends:
    def test_factory_is_called_on_resolve(self):
        calls = []

        def factory():
            calls.append(1)
            return "db-connection"

        dep = Depends(factory=factory)
        result = dep.resolve()
        assert result == "db-connection"
        assert len(calls) == 1

    def test_cached_factory_called_once(self):
        calls = []

        def factory():
            calls.append(1)
            return "conn"

        dep = Depends(factory=factory, cached=True)
        dep.resolve()
        dep.resolve()
        assert len(calls) == 1

    def test_non_cached_factory_called_each_time(self):
        calls = []

        def factory():
            calls.append(1)
            return "conn"

        dep = Depends(factory=factory, cached=False)
        dep.resolve()
        dep.resolve()
        assert len(calls) == 2


# ---------------------------------------------------------------------------
# _resolve_deps
# ---------------------------------------------------------------------------


class TestResolveDeps:
    def test_correct_type_passes(self):
        deps = SimpleDeps(db_url="u", api_key="k")
        result = _resolve_deps(SimpleDeps, deps)
        assert result is deps

    def test_wrong_type_raises(self):
        with pytest.raises(DependencyError, match="type mismatch"):
            _resolve_deps(SimpleDeps, EmptyDeps())

    def test_none_with_required_type_raises(self):
        with pytest.raises(DependencyError, match="required"):
            _resolve_deps(SimpleDeps, None)


# ---------------------------------------------------------------------------
# TypedAgent - basic construction
# ---------------------------------------------------------------------------


class TestTypedAgentBasic:
    def test_registers_tool(self):
        agent = TypedAgent(deps_type=SimpleDeps, name="test")

        @agent.tool
        def my_tool(ctx: RunContext[SimpleDeps]) -> str:
            return "hello"

        assert "my_tool" in agent.tool_names()

    def test_tool_decorator_returns_original_function(self):
        agent = TypedAgent(deps_type=SimpleDeps)

        @agent.tool
        def greet(ctx: RunContext[SimpleDeps]) -> str:
            return "hi"

        assert callable(greet)

    def test_multiple_tools_registered(self):
        agent = TypedAgent(deps_type=SimpleDeps)

        @agent.tool
        def tool_a(ctx: RunContext[SimpleDeps]) -> str:
            return "a"

        @agent.tool
        def tool_b(ctx: RunContext[SimpleDeps]) -> str:
            return "b"

        assert set(agent.tool_names()) == {"tool_a", "tool_b"}


# ---------------------------------------------------------------------------
# TypedAgent - synchronous run
# ---------------------------------------------------------------------------


class TestTypedAgentSyncRun:
    def test_sync_tool_receives_correct_deps(self):
        agent = TypedAgent(deps_type=SimpleDeps)
        received: list[str] = []

        @agent.tool
        def capture(ctx: RunContext[SimpleDeps]) -> str:
            received.append(ctx.deps.db_url)
            return ctx.deps.db_url

        deps = SimpleDeps(db_url="postgres://test", api_key="secret")
        run = agent.run_sync("test query", deps=deps)
        assert run.ok
        assert received == ["postgres://test"]

    def test_sync_run_output_from_last_tool(self):
        agent = TypedAgent(deps_type=SimpleDeps)

        @agent.tool
        def first(ctx: RunContext[SimpleDeps]) -> str:
            return "first"

        @agent.tool
        def second(ctx: RunContext[SimpleDeps]) -> str:
            return "second"

        deps = SimpleDeps(db_url="u", api_key="k")
        run = agent.run_sync("query", deps=deps)
        assert run.output == "second"

    def test_run_result_includes_run_id(self):
        agent = TypedAgent(deps_type=EmptyDeps)

        @agent.tool
        def noop(ctx: RunContext[EmptyDeps]) -> None:
            pass

        run = agent.run_sync("q", deps=EmptyDeps())
        assert len(run.run_id) > 0

    def test_wrong_deps_type_causes_failure(self):
        agent = TypedAgent(deps_type=SimpleDeps)

        @agent.tool
        def noop(ctx: RunContext[SimpleDeps]) -> None:
            pass

        with pytest.raises(DependencyError):
            agent.run_sync("q", deps=EmptyDeps())

    def test_failing_tool_marks_run_not_ok(self):
        agent = TypedAgent(deps_type=EmptyDeps)

        @agent.tool
        def boom(ctx: RunContext[EmptyDeps]) -> None:
            raise ValueError("deliberate failure")

        run = agent.run_sync("q", deps=EmptyDeps())
        assert run.ok is False
        assert run.error is not None

    def test_specific_tool_by_name(self):
        agent = TypedAgent(deps_type=EmptyDeps)

        @agent.tool
        def alpha(ctx: RunContext[EmptyDeps]) -> str:
            return "alpha"

        @agent.tool
        def beta(ctx: RunContext[EmptyDeps]) -> str:
            return "beta"

        run = agent.run_sync("q", deps=EmptyDeps(), tool_name="alpha")
        assert run.output == "alpha"
        assert all(r.tool_name == "alpha" for r in run.tool_results)


# ---------------------------------------------------------------------------
# TypedAgent - async run
# ---------------------------------------------------------------------------


class TestTypedAgentAsyncRun:
    def test_async_tool_receives_deps(self):
        agent = TypedAgent(deps_type=SimpleDeps)
        captured: list[str] = []

        @agent.tool
        async def fetch(ctx: RunContext[SimpleDeps]) -> str:
            captured.append(ctx.deps.api_key)
            return ctx.deps.api_key

        deps = SimpleDeps(db_url="u", api_key="api-test-key")
        run = asyncio.run(agent.run("query", deps=deps))
        assert run.ok
        assert captured == ["api-test-key"]

    def test_async_tool_error_marks_run_failed(self):
        agent = TypedAgent(deps_type=EmptyDeps)

        @agent.tool
        async def bad(ctx: RunContext[EmptyDeps]) -> None:
            raise RuntimeError("async failure")

        run = asyncio.run(agent.run("q", deps=EmptyDeps()))
        assert run.ok is False


# ---------------------------------------------------------------------------
# ToolResult and AgentRun serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_tool_result_to_dict(self):
        tr = ToolResult(ok=True, tool_name="my_tool", output={"x": 1})
        d = tr.to_dict()
        assert d["ok"] is True
        assert d["tool_name"] == "my_tool"
        assert d["output"] == {"x": 1}

    def test_agent_run_to_dict(self):
        agent = TypedAgent(deps_type=EmptyDeps)

        @agent.tool
        def noop(ctx: RunContext[EmptyDeps]) -> str:
            return "result"

        run = agent.run_sync("test", deps=EmptyDeps())
        d = run.to_dict()
        assert "run_id" in d
        assert "tool_results" in d
        assert isinstance(d["tool_results"], list)

    def test_run_workspace_id_reflected_in_dict(self):
        agent = TypedAgent(deps_type=EmptyDeps)

        @agent.tool
        def noop(ctx: RunContext[EmptyDeps]) -> str:
            return "x"

        run = agent.run_sync("q", deps=EmptyDeps(), workspace_id="my-workspace")
        d = run.to_dict()
        assert d["workspace_id"] == "my-workspace"


# ---------------------------------------------------------------------------
# Persona annotation on TypedAgent
# ---------------------------------------------------------------------------


class TestPersonaAnnotation:
    def test_persona_set_on_agent(self):
        agent = TypedAgent(deps_type=EmptyDeps, persona="FORGE")
        assert agent.persona == "FORGE"

    def test_persona_propagated_to_context(self):
        agent = TypedAgent(deps_type=EmptyDeps, persona="SAGE")
        captured: list[str | None] = []

        @agent.tool
        def read_persona(ctx: RunContext[EmptyDeps]) -> None:
            captured.append(ctx.persona)

        agent.run_sync("q", deps=EmptyDeps())
        assert captured == ["SAGE"]

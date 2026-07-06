"""
Typed dependency injection framework for keprix agent apps.

Pydantic AI-style DI: declare a typed deps container, pass it at run time,
receive it inside tools via RunContext[DepsT].

Usage:

    from dataclasses import dataclass
    from keprix.agent_apps.dependencies import RunContext, TypedAgent

    @dataclass
    class MyDeps:
        db_url: str
        api_key: str

    agent = TypedAgent(deps_type=MyDeps, name="my-agent")

    @agent.tool
    def fetch_record(ctx: RunContext[MyDeps], record_id: str) -> dict:
        # ctx.deps.db_url is validated and available
        return {"url": ctx.deps.db_url, "id": record_id}

    result = agent.run_sync("fetch record 42", deps=MyDeps(db_url="...", api_key="..."))
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar, get_type_hints

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


class DependencyError(Exception):
    """Raised when a required dependency is missing or fails validation."""


@dataclass
class RunContext(Generic[DepsT]):
    """Injected context received by every tool registered on a TypedAgent."""

    deps: DepsT
    run_id: str
    workspace_id: str
    query: str = ""
    persona: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Depends:
    """
    Declare a dependency factory for a field.

    Example:
        @dataclass
        class MyDeps:
            connection: str = field(default_factory=Depends(make_connection))
    """

    factory: Callable[[], Any]
    cached: bool = True
    _cache: Any = field(default=None, init=False, repr=False, compare=False)

    def resolve(self) -> Any:
        if self.cached:
            if self._cache is None:
                object.__setattr__(self, "_cache", self.factory())
            return self._cache
        return self.factory()


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    output: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class AgentRun(Generic[OutputT]):
    run_id: str
    query: str
    workspace_id: str
    tool_results: list[ToolResult] = field(default_factory=list)
    output: OutputT | None = None
    ok: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "query": self.query,
            "workspace_id": self.workspace_id,
            "tool_results": [r.to_dict() for r in self.tool_results],
            "output": self.output,
            "ok": self.ok,
            "error": self.error,
        }


def _resolve_deps(deps_type: type, deps: Any) -> Any:
    """Validate and resolve a deps instance against its declared type."""
    if deps is None and deps_type is type(None):
        return None
    if deps is None:
        raise DependencyError(f"deps required but not provided (expected {deps_type.__name__})")
    if not isinstance(deps, deps_type):
        raise DependencyError(
            f"deps type mismatch: expected {deps_type.__name__}, got {type(deps).__name__}"
        )
    if dataclasses.is_dataclass(deps):
        for f in dataclasses.fields(deps):
            value = getattr(deps, f.name)
            if isinstance(value, Depends):
                object.__setattr__(deps, f.name, value.resolve())
    return deps


class TypedAgent(Generic[DepsT]):
    """
    A keprix agent that declares typed dependencies and routes queries
    through registered tools.

    Modelled on the Pydantic AI Agent[DepsT, OutputT] pattern but
    implemented from scratch under MIT licence.
    """

    def __init__(
        self,
        *,
        deps_type: type[DepsT],
        name: str = "typed-agent",
        persona: str | None = None,
    ) -> None:
        self.deps_type = deps_type
        self.name = name
        self.persona = persona
        self._tools: dict[str, Callable] = {}

    def tool(self, func: Callable) -> Callable:
        """Register a callable as a tool on this agent."""
        self._tools[func.__name__] = func
        return func

    def tool_names(self) -> list[str]:
        return list(self._tools)

    def _make_context(
        self,
        deps: DepsT,
        *,
        query: str,
        workspace_id: str,
        run_id: str,
    ) -> RunContext[DepsT]:
        return RunContext(
            deps=deps,
            run_id=run_id,
            workspace_id=workspace_id,
            query=query,
            persona=self.persona,
        )

    async def run(
        self,
        query: str,
        *,
        deps: DepsT,
        workspace_id: str = "default",
        tool_name: str | None = None,
        tool_kwargs: dict[str, Any] | None = None,
    ) -> AgentRun:
        """
        Execute one agent run.

        If tool_name is provided the named tool is called directly.
        Otherwise all registered tools are called in registration order
        and their results collected.
        """
        run_id = str(uuid.uuid4())
        resolved_deps = _resolve_deps(self.deps_type, deps)
        ctx = self._make_context(
            resolved_deps,
            query=query,
            workspace_id=workspace_id,
            run_id=run_id,
        )
        run: AgentRun = AgentRun(run_id=run_id, query=query, workspace_id=workspace_id)

        targets = (
            {tool_name: self._tools[tool_name]}
            if tool_name and tool_name in self._tools
            else self._tools
        )

        for name, func in targets.items():
            try:
                kwargs = tool_kwargs or {}
                if inspect.iscoroutinefunction(func):
                    output = await func(ctx, **kwargs)
                else:
                    output = func(ctx, **kwargs)
                run.tool_results.append(ToolResult(ok=True, tool_name=name, output=output))
            except Exception as exc:
                run.tool_results.append(
                    ToolResult(ok=False, tool_name=name, error=str(exc))
                )
                run.ok = False

        if run.tool_results:
            last = run.tool_results[-1]
            run.output = last.output if last.ok else None
            if not run.ok and not run.error:
                first_error = next((r.error for r in run.tool_results if r.error), None)
                run.error = first_error

        return run

    def run_sync(
        self,
        query: str,
        *,
        deps: DepsT,
        workspace_id: str = "default",
        tool_name: str | None = None,
        tool_kwargs: dict[str, Any] | None = None,
    ) -> AgentRun:
        """Synchronous wrapper around run()."""
        return asyncio.run(
            self.run(
                query,
                deps=deps,
                workspace_id=workspace_id,
                tool_name=tool_name,
                tool_kwargs=tool_kwargs,
            )
        )

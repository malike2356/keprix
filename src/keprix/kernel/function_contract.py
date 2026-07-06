"""Typed function contracts and invocation."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable


class InvocationKind(str, Enum):
    NATIVE = "native"
    HTTP = "http"
    MCP = "mcp"
    AGENT = "agent"
    PLAYBOOK = "playbook"


@dataclass
class FunctionContract:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    invocation: InvocationKind = InvocationKind.NATIVE
    risk_level: str = "low"
    permissions: list[str] = field(default_factory=list)
    cost_units: int = 1
    output_type: str = "text"
    handler: Callable[[dict[str, Any], dict[str, Any]], Any] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("handler", None)
        data["invocation"] = self.invocation.value
        return data


@dataclass
class InvocationTrace:
    trace_id: str
    plugin_name: str
    function_name: str
    status: str
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_traces: list[InvocationTrace] = []


def get_invocation_traces() -> list[dict[str, Any]]:
    return [trace.to_dict() for trace in _traces]


def clear_invocation_traces() -> None:
    _traces.clear()


def invoke_function(
    plugin_name: str,
    function: FunctionContract,
    arguments: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace_id = str(uuid.uuid4())
    ctx = dict(context or {})
    try:
        if function.invocation == InvocationKind.NATIVE:
            if function.handler is None:
                raise RuntimeError(f"Native function `{function.name}` has no handler")
            result = function.handler(arguments, ctx)
            if not isinstance(result, dict):
                result = {"result": result}
        elif function.invocation == InvocationKind.HTTP:
            result = {"status": "queued", "url": ctx.get("url"), "payload": arguments}
        elif function.invocation == InvocationKind.MCP:
            result = {"status": "delegated", "transport": "mcp", "tool": function.name, "args": arguments}
        elif function.invocation == InvocationKind.AGENT:
            result = {"status": "delegated", "transport": "agent", "task": arguments}
        elif function.invocation == InvocationKind.PLAYBOOK:
            result = {"status": "delegated", "transport": "playbook", "node": function.name, "state": arguments}
        else:
            raise RuntimeError(f"Unsupported invocation kind: {function.invocation}")
        trace = InvocationTrace(
            trace_id=trace_id,
            plugin_name=plugin_name,
            function_name=function.name,
            status="ok",
            input=arguments,
            output=result,
        )
        _traces.append(trace)
        return {"trace_id": trace_id, "status": "ok", "output": result}
    except Exception as exc:
        trace = InvocationTrace(
            trace_id=trace_id,
            plugin_name=plugin_name,
            function_name=function.name,
            status="error",
            input=arguments,
            error=str(exc),
        )
        _traces.append(trace)
        return {"trace_id": trace_id, "status": "error", "error": str(exc)}

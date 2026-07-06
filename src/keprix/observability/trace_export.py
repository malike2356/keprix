"""Trace export for agent runtime runs."""

from __future__ import annotations

from typing import Any

from keprix.agents_runtime.run_context import RunContext
from keprix.observability.trace_view import build_trace_view


def export_trace(ctx: RunContext) -> dict[str, Any]:
    view = build_trace_view(ctx)
    return {
        "format": "keprix-agent-trace-v1",
        "run_id": ctx.run_id,
        "state": dict(ctx.state),
        **view,
    }

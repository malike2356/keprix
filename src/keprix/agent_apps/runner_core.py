"""Resolve and execute agent app entrypoints."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from keprix.agent_apps.agent_runtime import (
    AgentAppEnvError,
    AgentAppPermissionError,
    run_agent_app_llm_sync,
)
from keprix.agent_apps.app_manifest import AgentAppManifest, load_manifest
from keprix.agent_apps.lifecycle import LifecycleBus, LifecycleEvent, store_run_traces
from keprix.agent_apps.run_store import record_run_finish, record_run_start


def resolve_entrypoint(manifest: AgentAppManifest, entrypoint: str | None = None) -> Callable[..., Any]:
    assert manifest.app_dir is not None
    target = entrypoint or manifest.entrypoint
    module_name, func_name = target.split(":", 1)
    module_path = manifest.app_dir / f"{module_name.replace('.', '/')}.py"
    app_dir = str(manifest.app_dir)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load entrypoint module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    func = getattr(module, func_name, None)
    if func is None or not callable(func):
        raise ImportError(f"Entrypoint callable not found: {target}")
    return func


def _merge_run_input(
    manifest: AgentAppManifest,
    input_text: str,
    context: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    context = dict(context or {})
    form = context.get("form") or context.get("inputs")
    if not isinstance(form, dict):
        form = {}
    if input_text.strip() and not form and manifest.inputs:
        first_text_input = next(
            (item for item in manifest.inputs if item.type in ("text", "textarea")),
            None,
        )
        if first_text_input is not None:
            form = {first_text_input.id: input_text}
    elif not input_text.strip() and form:
        first_text = next((str(value) for value in form.values() if str(value).strip()), "")
        input_text = first_text
    context["form"] = form
    return input_text, context


def _run_python_entrypoint(
    manifest: AgentAppManifest,
    *,
    input_text: str,
    context: dict[str, Any],
    entrypoint: str | None = None,
) -> dict[str, Any]:
    assert manifest.app_dir is not None
    entrypoint_fn = resolve_entrypoint(manifest, entrypoint=entrypoint)
    result = entrypoint_fn(input_text, context=context)
    if not isinstance(result, dict):
        result = {"output": str(result)}
    return result


def run_agent_app(
    app_dir: Path,
    *,
    input_text: str,
    context: dict[str, Any] | None = None,
    runner: str = "local",
    user_id: str | None = None,
) -> dict[str, Any]:
    manifest = load_manifest(app_dir)
    input_text, context = _merge_run_input(manifest, input_text, context)
    bus = LifecycleBus(app_name=manifest.name)
    started_at = datetime.now(timezone.utc).isoformat()
    record_run_start(
        trace_id=bus.trace_id,
        app_name=manifest.name,
        runner=runner,
        input_payload={"input": input_text, "context": context},
        user_id=user_id,
    )
    bus.emit(LifecycleEvent.BEFORE_RUN, {"runner": runner, "input": input_text, "context": context})
    try:
        if manifest.runtime == "python":
            result = _run_python_entrypoint(manifest, input_text=input_text, context=context)
        elif manifest.runtime == "hybrid":
            if manifest.pre_entrypoint:
                pre_result = _run_python_entrypoint(
                    manifest,
                    input_text=input_text,
                    context=context,
                    entrypoint=manifest.pre_entrypoint,
                )
                if isinstance(pre_result, dict):
                    context = {**context, "prehook": pre_result}
            result = run_agent_app_llm_sync(app_dir, manifest, input_text=input_text, context=context)
        else:
            result = run_agent_app_llm_sync(app_dir, manifest, input_text=input_text, context=context)
        bus.emit(LifecycleEvent.AFTER_RUN, {"status": result.get("status", "ok")})
        if result.get("artifact"):
            bus.emit(LifecycleEvent.ON_ARTIFACT_CREATED, {"artifact": result["artifact"]})
        store_run_traces(manifest.name, bus.traces, trace_id=bus.trace_id)
        record_run_finish(
            trace_id=bus.trace_id,
            status="success",
            output=result,
            started_at=started_at,
        )
        return {
            "app": manifest.name,
            "version": manifest.version,
            "runner": runner,
            "trace_id": bus.trace_id,
            "result": result,
            "traces": [trace.to_dict() for trace in bus.traces],
        }
    except AgentAppPermissionError as exc:
        bus.emit(
            LifecycleEvent.ON_APPROVAL_REQUESTED,
            {"missing_permissions": exc.missing, "error": str(exc)},
        )
        store_run_traces(manifest.name, bus.traces, trace_id=bus.trace_id)
        record_run_finish(
            trace_id=bus.trace_id,
            status="error",
            error=str(exc),
            started_at=started_at,
        )
        raise
    except Exception as exc:
        bus.emit(LifecycleEvent.ON_ERROR, {"error": str(exc)})
        store_run_traces(manifest.name, bus.traces, trace_id=bus.trace_id)
        record_run_finish(
            trace_id=bus.trace_id,
            status="error",
            error=str(exc),
            started_at=started_at,
        )
        raise

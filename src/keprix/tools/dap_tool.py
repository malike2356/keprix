"""Gated agent tools for structured Debug Adapter Protocol sessions."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

from keprix.agent.dap.adapters import adapter_available
from keprix.agent.dap.session import create_debug_session, get_debug_sessions, stop_debug_session
from tools.registry import registry


def _debug_enabled() -> bool:
    try:
        from keprix_cli.config import load_config

        cfg = load_config() or {}
        return bool((cfg.get("debug") or {}).get("enabled", False)) and any(
            adapter_available(language) for language in ("python", "rust", "c_cpp", "go")
        )
    except Exception:
        return False


def _run(coro: Awaitable[Any]) -> str:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return json.dumps(asyncio.run(coro), ensure_ascii=False)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return json.dumps(pool.submit(asyncio.run, coro).result(), ensure_ascii=False)


async def _session(session_id: str):
    session = (await get_debug_sessions()).get(session_id)
    if session is None:
        raise ValueError(f"unknown debug session: {session_id}")
    return session


async def _launch(args: dict[str, Any]) -> dict[str, Any]:
    language = str(args.get("language") or "python")
    session = await create_debug_session(language, cwd=args.get("cwd"))
    try:
        result = await session.launch(str(args["program"]), list(args.get("args") or []))
        return {"session_id": session.id, "status": "launched", "adapter": language, "result": result}
    except Exception:
        await stop_debug_session(session.id)
        raise


async def _attach(args: dict[str, Any]) -> dict[str, Any]:
    session = await create_debug_session(str(args.get("language") or "python"), cwd=args.get("cwd"))
    try:
        result = await session.attach(int(args["pid"]))
        return {"session_id": session.id, "status": "attached", "result": result}
    except Exception:
        await stop_debug_session(session.id)
        raise


async def _action(args: dict[str, Any], action: str) -> dict[str, Any]:
    session = await _session(str(args.get("session_id") or ""))
    if action == "breakpoint":
        return await session.set_breakpoint(str(args["path"]), int(args["line"]))
    if action == "continue":
        return await session.continue_execution(int(args.get("thread_id") or 1))
    if action == "step":
        return await session.step(str(args.get("kind") or "over"), int(args.get("thread_id") or 1))
    if action == "frames":
        return await session.frames(int(args.get("thread_id") or 1))
    if action == "variables":
        return await session.variables(int(args["variables_reference"]))
    if action == "evaluate":
        return await session.evaluate(str(args["expression"]), args.get("frame_id"))
    raise ValueError(f"unknown debug action: {action}")


def _handler(action: str) -> Callable[..., str]:
    def handle(args: dict[str, Any], **_: Any) -> str:
        if action == "launch":
            return _run(_launch(args))
        if action == "attach":
            return _run(_attach(args))
        if action == "stop":
            return _run(stop_debug_session(str(args.get("session_id") or "")))
        return _run(_action(args, action))

    return handle


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}


COMMON_SESSION = {"session_id": {"type": "string"}}
registry.register(
    name="debug_launch",
    toolset="debug",
    schema=_schema("debug_launch", "Launch a structured program under a DAP debugger.", {"language": {"type": "string"}, "program": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}, "cwd": {"type": "string"}}, ["program"]),
    handler=_handler("launch"),
    check_fn=_debug_enabled,
)
registry.register(
    name="debug_attach",
    toolset="debug",
    schema=_schema("debug_attach", "Attach a DAP debugger to a process id.", {"language": {"type": "string"}, "pid": {"type": "integer"}, "cwd": {"type": "string"}}, ["pid"]),
    handler=_handler("attach"),
    check_fn=_debug_enabled,
)
registry.register(
    name="debug_set_breakpoint",
    toolset="debug",
    schema=_schema("debug_set_breakpoint", "Set a source breakpoint in a debug session.", {**COMMON_SESSION, "path": {"type": "string"}, "line": {"type": "integer"}}, ["session_id", "path", "line"]),
    handler=_handler("breakpoint"),
    check_fn=_debug_enabled,
)
registry.register(name="debug_continue", toolset="debug", schema=_schema("debug_continue", "Continue a debug session.", {**COMMON_SESSION, "thread_id": {"type": "integer"}}, ["session_id"]), handler=_handler("continue"), check_fn=_debug_enabled)
registry.register(name="debug_step", toolset="debug", schema=_schema("debug_step", "Step over, into, or out of the current frame.", {**COMMON_SESSION, "kind": {"type": "string", "enum": ["over", "in", "out"]}, "thread_id": {"type": "integer"}}, ["session_id"]), handler=_handler("step"), check_fn=_debug_enabled)
registry.register(name="debug_frames", toolset="debug", schema=_schema("debug_frames", "Read stack frames for a debug thread.", {**COMMON_SESSION, "thread_id": {"type": "integer"}}, ["session_id"]), handler=_handler("frames"), check_fn=_debug_enabled)
registry.register(name="debug_variables", toolset="debug", schema=_schema("debug_variables", "Read variables from a debug scope reference.", {**COMMON_SESSION, "variables_reference": {"type": "integer"}}, ["session_id", "variables_reference"]), handler=_handler("variables"), check_fn=_debug_enabled)
registry.register(name="debug_evaluate", toolset="debug", schema=_schema("debug_evaluate", "Evaluate an expression in a debug frame.", {**COMMON_SESSION, "expression": {"type": "string"}, "frame_id": {"type": "integer"}}, ["session_id", "expression"]), handler=_handler("evaluate"), check_fn=_debug_enabled)
registry.register(
    name="debug_stop",
    toolset="debug",
    schema=_schema("debug_stop", "Terminate and clean up a debug session.", COMMON_SESSION, ["session_id"]),
    handler=_handler("stop"),
    check_fn=_debug_enabled,
)

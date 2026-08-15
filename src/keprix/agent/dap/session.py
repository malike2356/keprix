"""In-memory debug session lifecycle and high-level DAP operations."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from .adapters import adapter_command
from .client import DapClient


class DebugSession:
    def __init__(self, language: str, *, cwd: str | None = None) -> None:
        self.id = f"dbg_{uuid.uuid4().hex[:16]}"
        self.language = language
        self.cwd = cwd or os.getcwd()
        self.client = DapClient(adapter_command(language), cwd=self.cwd)
        self.breakpoints: dict[str, list[dict[str, Any]]] = {}
        self._started = False

    async def launch(self, program: str, args: list[str] | None = None) -> dict[str, Any]:
        program_path = str(Path(program).resolve())
        await self.client.start()
        self._started = True
        if self.language == "python":
            launch_args = {"program": program_path, "args": list(args or []), "cwd": self.cwd, "console": "internalConsole"}
        else:
            launch_args = {"program": program_path, "args": list(args or []), "cwd": self.cwd}
        return await self.client.request("launch", launch_args)

    async def attach(self, pid: int) -> dict[str, Any]:
        await self.client.start()
        self._started = True
        return await self.client.request("attach", {"processId": int(pid)})

    async def configure(self) -> dict[str, Any]:
        return await self.client.request("configurationDone")

    async def set_breakpoint(self, path: str, line: int) -> dict[str, Any]:
        source = str(Path(path).resolve())
        body = await self.client.request("setBreakpoints", {"source": {"path": source}, "breakpoints": [{"line": int(line)}]})
        self.breakpoints[source] = list(body.get("breakpoints") or [])
        return {"source": source, "breakpoints": self.breakpoints[source]}

    async def continue_execution(self, thread_id: int = 1) -> dict[str, Any]:
        return await self.client.request("continue", {"threadId": int(thread_id)})

    async def step(self, kind: str, thread_id: int = 1) -> dict[str, Any]:
        command = {"over": "next", "in": "stepIn", "out": "stepOut"}.get(kind)
        if command is None:
            raise ValueError("step kind must be over, in, or out")
        return await self.client.request(command, {"threadId": int(thread_id)})

    async def frames(self, thread_id: int = 1) -> dict[str, Any]:
        return await self.client.request("stackTrace", {"threadId": int(thread_id)})

    async def variables(self, variables_reference: int) -> dict[str, Any]:
        return await self.client.request("variables", {"variablesReference": int(variables_reference)})

    async def evaluate(self, expression: str, frame_id: int | None = None) -> dict[str, Any]:
        arguments: dict[str, Any] = {"expression": expression, "context": "repl"}
        if frame_id is not None:
            arguments["frameId"] = int(frame_id)
        return await self.client.request("evaluate", arguments)

    async def stop(self) -> None:
        if self._started:
            try:
                await self.client.request("disconnect", {"terminateDebuggee": True}, timeout=3.0)
            except Exception:  # noqa: BLE001
                pass
        await self.client.stop()


_sessions: dict[str, DebugSession] = {}
_lock = asyncio.Lock()


async def get_debug_sessions() -> dict[str, DebugSession]:
    return dict(_sessions)


async def create_debug_session(language: str, *, cwd: str | None = None) -> DebugSession:
    session = DebugSession(language, cwd=cwd)
    async with _lock:
        _sessions[session.id] = session
    return session


async def stop_debug_session(session_id: str) -> bool:
    async with _lock:
        session = _sessions.pop(session_id, None)
    if session is None:
        return False
    await session.stop()
    return True


__all__ = ["DebugSession", "create_debug_session", "get_debug_sessions", "stop_debug_session"]

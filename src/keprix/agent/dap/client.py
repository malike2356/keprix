"""Minimal asynchronous DAP client over framed stdio."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger("keprix.dap")


class DapError(RuntimeError):
    pass


class DapClient:
    def __init__(self, command: list[str], *, cwd: str | None = None) -> None:
        self.command = list(command)
        self.cwd = cwd
        self.process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._next_seq = 1
        self._events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def start(self) -> None:
        if self.process is not None:
            return
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        await self.request(
            "initialize",
            {
                "clientID": "keprix",
                "clientName": "Keprix",
                "adapterID": "keprix",
                "pathFormat": "path",
                "linesStartAt1": False,
                "columnsStartAt1": False,
                "supportsRunInTerminalRequest": False,
            },
        )
        await self.notify("initialized", {})

    async def request(self, command: str, arguments: dict[str, Any] | None = None, *, timeout: float = 15.0) -> Any:
        if self.process is None or self.process.stdin is None:
            raise DapError("debug adapter is not running")
        loop = asyncio.get_running_loop()
        seq = self._next_seq
        self._next_seq += 1
        future = loop.create_future()
        self._pending[seq] = future
        await self._write({"seq": seq, "type": "request", "command": command, "arguments": arguments or {}})
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(seq, None)

    async def notify(self, event: str, body: dict[str, Any] | None = None) -> None:
        await self._write({"seq": self._next_seq, "type": "event", "event": event, "body": body or {}})
        self._next_seq += 1

    async def next_event(self, *, timeout: float = 15.0) -> dict[str, Any]:
        return await asyncio.wait_for(self._events.get(), timeout=timeout)

    async def _write(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise DapError("debug adapter is not running")
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
        self.process.stdin.write(b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n\r\n" + payload)
        await self.process.stdin.drain()

    async def _read_loop(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        reader = self.process.stdout
        try:
            while True:
                header = await reader.readuntil(b"\r\n\r\n")
                length = next((int(line.split(b":", 1)[1].strip()) for line in header.splitlines() if line.lower().startswith(b"content-length:")), None)
                if length is None:
                    raise DapError("DAP message has no Content-Length")
                message = json.loads((await reader.readexactly(length)).decode("utf-8"))
                if message.get("type") == "response":
                    future = self._pending.get(int(message.get("request_seq", -1)))
                    if future is None or future.done():
                        continue
                    if not message.get("success", False):
                        future.set_exception(DapError(str(message.get("message") or "DAP request failed")))
                    else:
                        future.set_result(message.get("body") or {})
                elif message.get("type") == "event":
                    await self._events.put(message)
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
            pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("DAP reader stopped: %s", exc)
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(exc)

    async def stop(self, *, terminate: bool = True) -> None:
        process = self.process
        self.process = None
        if self._reader_task is not None:
            self._reader_task.cancel()
            await asyncio.gather(self._reader_task, return_exceptions=True)
            self._reader_task = None
        if process is not None and process.returncode is None:
            if terminate:
                process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

"""WebSocket-based gateway client for keprix TUI.

Adds real-time WebSocket connectivity to the existing HTTP KeprixClient.
The TUI can now receive streaming deltas, tool call progress, and turn
status updates via a persistent WebSocket connection instead of polling.

Used by: tui/app.py (KeprixTuiApp)
Compatible with: existing HTTP KeprixClient (falls back gracefully)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable

logger = logging.getLogger(__name__)


@dataclass
class StreamDelta:
    """A single token delta from streaming output."""
    text: str
    turn_id: str = ""
    is_reasoning: bool = False


@dataclass
class ToolCallProgress:
    """Progress update for a running tool call."""
    tool_name: str
    tool_call_id: str = ""
    status: str = "running"  # running, completed, error
    message: str = ""


@dataclass
class TurnStatusUpdate:
    """Turn-level status update from the gateway."""
    busy: bool
    mode: str = ""
    queue_depth: int = 0


@dataclass
class GatewayConfig:
    """Gateway WebSocket connection configuration."""
    ws_url: str = ""
    reconnect_initial_delay: float = 1.0
    reconnect_max_delay: float = 30.0
    reconnect_backoff: float = 2.0
    ping_interval: float = 30.0
    ping_timeout: float = 10.0


# Callback types
DeltaCallback = Callable[[StreamDelta], None]
ToolProgressCallback = Callable[[ToolCallProgress], None]
TurnStatusCallback = Callable[[TurnStatusUpdate], None]
ErrorCallback = Callable[[str], None]


class GatewayWebSocket:
    """Persistent WebSocket connection for TUI gateway communication."""

    def __init__(
        self,
        ws_url: str,
        token: str | None = None,
        config: GatewayConfig | None = None,
    ) -> None:
        self.ws_url = ws_url.rstrip("/")
        self.token = token
        self.config = config or GatewayConfig(ws_url=ws_url)
        self._ws: Any = None
        self._connected: bool = False
        self._running: bool = False
        self._reconnect_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._receive_task: asyncio.Task | None = None

        # Callbacks
        self.on_delta: DeltaCallback | None = None
        self.on_tool_progress: ToolProgressCallback | None = None
        self.on_turn_status: TurnStatusCallback | None = None
        self.on_error: ErrorCallback | None = None
        self.on_reconnect: Callable[[int], None] | None = None  # attempt number

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Establish WebSocket connection with retry."""
        self._running = True
        await self._connect_with_retry()

    async def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        self._running = False
        if self._reconnect_task:
            self._reconnect_task.cancel()
        if self._ping_task:
            self._ping_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._connected = False

    async def send(self, message: dict[str, Any]) -> None:
        """Send a JSON message over the WebSocket."""
        if not self._ws or not self._connected:
            logger.warning("Cannot send: WebSocket not connected")
            return
        try:
            await self._ws.send(json.dumps(message))
        except Exception as e:
            logger.error("WebSocket send failed: %s", e)
            if self.on_error:
                self.on_error(f"Send failed: {e}")

    async def _connect_with_retry(self) -> None:
        """Connect with exponential backoff retry."""
        attempt = 0
        while self._running:
            attempt += 1
            try:
                await self._do_connect()
                logger.info("Gateway WebSocket connected (attempt %d)", attempt)
                if self.on_reconnect:
                    self.on_reconnect(attempt)
                return
            except Exception as e:
                delay = min(
                    self.config.reconnect_initial_delay * (self.config.reconnect_backoff ** (attempt - 1)),
                    self.config.reconnect_max_delay,
                )
                logger.warning(
                    "WebSocket connection attempt %d failed: %s. Retrying in %.1fs",
                    attempt, e, delay,
                )
                if self.on_error:
                    self.on_error(f"Connection failed (attempt {attempt}): {e}")
                await asyncio.sleep(delay)

    async def _do_connect(self) -> None:
        """Perform a single WebSocket connection attempt."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets package not installed. Install with: pip install websockets")
            if self.on_error:
                self.on_error("WebSocket support not available: install 'websockets' package")
            return

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        ws_url = self.ws_url
        if not ws_url.startswith(("ws://", "wss://")):
            # Derive WS URL from HTTP base URL
            ws_url = ws_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = f"{ws_url}/api/ws/tui"

        self._ws = await websockets.connect(
            ws_url,
            extra_headers=headers,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_timeout,
        )
        self._connected = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def _receive_loop(self) -> None:
        """Receive messages from the WebSocket and dispatch to callbacks."""
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                    self._dispatch(msg)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from WebSocket: %.100s", raw)
                except Exception as e:
                    logger.exception("Error dispatching WebSocket message")
                    if self.on_error:
                        self.on_error(f"Message dispatch error: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("WebSocket receive loop error: %s", e)
            self._connected = False
            if self.on_error:
                self.on_error(f"Connection lost: {e}")
            # Auto-reconnect
            if self._running:
                asyncio.create_task(self._reconnect())

    async def _ping_loop(self) -> None:
        """Keep-alive ping loop."""
        try:
            while self._running and self._connected:
                await asyncio.sleep(self.config.ping_interval)
                if self._ws:
                    try:
                        await self._ws.ping()
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass

    async def _reconnect(self) -> None:
        """Reconnect after connection loss."""
        self._connected = False
        if self._running:
            await asyncio.sleep(self.config.reconnect_initial_delay)
            await self._connect_with_retry()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        """Route an incoming message to the appropriate callback."""
        msg_type = msg.get("type", "")

        if msg_type == "delta":
            if self.on_delta:
                self.on_delta(StreamDelta(
                    text=msg.get("text", ""),
                    turn_id=msg.get("turn_id", ""),
                    is_reasoning=msg.get("is_reasoning", False),
                ))
        elif msg_type == "tool_progress":
            if self.on_tool_progress:
                self.on_tool_progress(ToolCallProgress(
                    tool_name=msg.get("tool_name", ""),
                    tool_call_id=msg.get("tool_call_id", ""),
                    status=msg.get("status", "running"),
                    message=msg.get("message", ""),
                ))
        elif msg_type == "turn_status":
            if self.on_turn_status:
                self.on_turn_status(TurnStatusUpdate(
                    busy=msg.get("busy", False),
                    mode=msg.get("mode", ""),
                    queue_depth=msg.get("queue_depth", 0),
                ))
        elif msg_type == "error":
            if self.on_error:
                self.on_error(msg.get("message", "Unknown error"))
        else:
            logger.debug("Unknown WebSocket message type: %s", msg_type)

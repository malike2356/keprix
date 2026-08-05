"""Runtime transport abstraction for the Keprix TUI."""

from keprix.tui.runtime_transport.base import RuntimeTransport
from keprix.tui.runtime_transport.events import RuntimeTransportEvent, normalize_runtime_event
from keprix.tui.runtime_transport.http import HttpRuntimeTransport
from keprix.tui.runtime_transport.in_process import InProcessRuntimeTransport
from keprix.tui.runtime_transport.selector import select_runtime_transport
from keprix.tui.runtime_transport.websocket import WebSocketRuntimeTransport

__all__ = [
    "HttpRuntimeTransport",
    "InProcessRuntimeTransport",
    "RuntimeTransport",
    "RuntimeTransportEvent",
    "WebSocketRuntimeTransport",
    "normalize_runtime_event",
    "select_runtime_transport",
]

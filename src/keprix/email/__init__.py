"""Keprix email integration module."""

from keprix.email.mcp_server import get_mcp_server
from keprix.email.pollers import start_email_poller, stop_email_poller
from keprix.email.routes import router
from keprix.email.store import get_email_store

__all__ = [
    "get_email_store",
    "get_mcp_server",
    "router",
    "start_email_poller",
    "stop_email_poller",
]

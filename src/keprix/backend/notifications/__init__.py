"""Unified notifications, inbox, and alert routing (Prompt 24)."""

from keprix.backend.notifications.inbox import get_inbox_service
from keprix.backend.notifications.routes import router

__all__ = ["get_inbox_service", "router"]

"""Outbound notifications to external recipients."""

from keprix.notify_external.routes import router
from keprix.notify_external.smtp_sender import send_email
from keprix.notify_external.store import get_notify_external_store, reset_notify_external_store
from keprix.notify_external.webhook_sender import send_webhook

__all__ = [
    "router",
    "send_email",
    "send_webhook",
    "get_notify_external_store",
    "reset_notify_external_store",
]

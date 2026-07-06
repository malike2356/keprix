"""Stripe webhook dispatch and handlers."""

from keprix.billing.webhooks.dispatcher import dispatch_webhook_event

__all__ = ["dispatch_webhook_event"]

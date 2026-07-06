"""Stripe integration for Keprix billing."""

from keprix.billing.stripe.client import get_stripe_client

__all__ = ["get_stripe_client"]

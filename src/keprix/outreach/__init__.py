"""Outreach automation package (K02)."""

from keprix.outreach.service import OutreachService, get_outreach_service
from keprix.outreach.store import get_outreach_store, reset_outreach_store_for_tests

__all__ = [
    "OutreachService",
    "get_outreach_service",
    "get_outreach_store",
    "reset_outreach_store_for_tests",
]

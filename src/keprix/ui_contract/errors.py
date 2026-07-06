"""Shared error tone and codes."""

from __future__ import annotations

ERROR_TONE: dict[str, str] = {
    "unauthorized": "Sign in to continue.",
    "forbidden": "You do not have permission for this action.",
    "not_found": "The requested item was not found.",
    "validation_error": "Check the highlighted fields and try again.",
    "internal_error": "Something went wrong. Try again or contact your administrator.",
    "rate_limited": "Too many attempts. Wait a moment and try again.",
}

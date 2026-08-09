"""Conferencing adapters for viCal (Prompt 632)."""

from keprix.vical.conferencing.fallback import (
    apply_meeting_url_on_confirm,
    calendar_sync_enabled,
    resolve_meeting_url,
    sync_notes,
)
from keprix.vical.conferencing.redact import redact_conferencing_payload, to_public_booking_view
from keprix.vical.conferencing.static_url_adapter import StaticUrlConferencingAdapter
from keprix.vical.conferencing.types import ConferenceAdapterResult, ConferencingAdapter
from keprix.vical.conferencing.zoom_adapter import ZoomConferencingAdapter, ZoomConferencingError

__all__ = [
    "ConferenceAdapterResult",
    "ConferencingAdapter",
    "StaticUrlConferencingAdapter",
    "ZoomConferencingAdapter",
    "ZoomConferencingError",
    "apply_meeting_url_on_confirm",
    "calendar_sync_enabled",
    "redact_conferencing_payload",
    "resolve_meeting_url",
    "sync_notes",
    "to_public_booking_view",
]

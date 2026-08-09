"""Labelled unmanaged static URL fallback (not managed Zoom sync)."""

from __future__ import annotations

from keprix.vical.conferencing.types import (
    ConferenceAdapterResult,
    ConferenceCreateInput,
    ConferenceDeleteInput,
    ConferenceUpdateInput,
)


class StaticUrlConferencingAdapter:
    provider = "static_url"

    def __init__(self, *, default_url: str | None = None) -> None:
        self.default_url = (default_url or "").strip() or None

    def create_meeting(self, input: ConferenceCreateInput) -> ConferenceAdapterResult:
        url = self.default_url
        if not url:
            return ConferenceAdapterResult(
                ok=True,
                provider="static_url",
                status="skipped",
                managed=False,
                detail="static_room_url_fallback:no_url",
            )
        return ConferenceAdapterResult(
            ok=True,
            provider="static_url",
            status="created",
            meeting_id=f"static:{input.idempotency_key[:24]}",
            join_url=url,
            managed=False,
            detail="static_room_url_fallback",
            metadata={"label": "unmanaged_static_url", "notManagedZoom": True},
        )

    def update_meeting(self, input: ConferenceUpdateInput) -> ConferenceAdapterResult:
        return ConferenceAdapterResult(
            ok=True,
            provider="static_url",
            status="updated",
            meeting_id=input.meeting_id,
            join_url=self.default_url,
            managed=False,
            detail="static_room_url_fallback",
        )

    def delete_meeting(self, input: ConferenceDeleteInput) -> ConferenceAdapterResult:
        return ConferenceAdapterResult(
            ok=True,
            provider="static_url",
            status="deleted",
            meeting_id=input.meeting_id,
            managed=False,
            detail="static_room_url_fallback",
        )

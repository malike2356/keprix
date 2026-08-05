"""API inspector runtime exports."""

from keprix.tui.runtime_events import ApiRuntimeEvent


def latest_api_event(events: list[ApiRuntimeEvent]) -> ApiRuntimeEvent | None:
    return events[-1] if events else None


__all__ = ["ApiRuntimeEvent", "latest_api_event"]

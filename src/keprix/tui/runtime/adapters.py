"""Runtime payload adapters."""

from typing import Any

from keprix.tui.runtime.events import ApiRuntimeEvent


def api_event_from_payload(payload: dict[str, Any]) -> ApiRuntimeEvent:
    return ApiRuntimeEvent(
        request_id=str(payload.get("request_id") or ""),
        provider=str(payload.get("provider") or ""),
        model=str(payload.get("model") or ""),
        status=str(payload.get("status") or ""),
        latency_ms=int(payload.get("latency_ms") or 0),
        input_tokens=int(payload.get("input_tokens") or 0),
        output_tokens=int(payload.get("output_tokens") or 0),
        error=str(payload.get("error") or ""),
    )


__all__ = ["api_event_from_payload"]

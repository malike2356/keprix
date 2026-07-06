"""Human interrupt helpers."""

from __future__ import annotations

from typing import Any

from keprix.playbook.runtime.errors import PlaybookInterrupt


def interrupt(
    reason: str,
    *,
    state_patch_schema: dict | None = None,
    approval_request: dict | None = None,
) -> None:
    """Pause execution until an operator resumes the run."""
    raise PlaybookInterrupt(
        reason,
        state_patch_schema=state_patch_schema,
        approval_request=approval_request,
    )


def merge_state_patch(state: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    if not patch:
        return state
    merged = dict(state)
    merged.update(patch)
    return merged

"""Normalize playbook node event payloads for run detail UI (Prompt 209)."""

from __future__ import annotations

import json
from typing import Any


DEFAULT_MAX_STATE_BYTES = 32768


def truncate_state(state: dict[str, Any] | None, *, max_bytes: int = DEFAULT_MAX_STATE_BYTES) -> dict[str, Any]:
    """Return *state* or a truncated preview when JSON encoding exceeds *max_bytes*."""
    if not state:
        return {}
    try:
        encoded = json.dumps(state, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        encoded = json.dumps({"_serialization_error": True}, ensure_ascii=False)
    byte_size = len(encoded.encode("utf-8"))
    if byte_size <= max_bytes:
        return dict(state)
    preview_limit = max(256, max_bytes // 2)
    return {
        "_truncated": True,
        "preview": encoded[:preview_limit],
        "byte_size": byte_size,
    }


def build_node_started_payload(
    *,
    node: str,
    input_state: dict[str, Any],
    max_bytes: int = DEFAULT_MAX_STATE_BYTES,
) -> dict[str, Any]:
    truncated = truncate_state(input_state, max_bytes=max_bytes)
    return {
        "node": node,
        "input_state": truncated,
        "state": truncated,
    }


def build_node_completed_payload(
    *,
    node: str,
    input_state: dict[str, Any],
    output_state: dict[str, Any],
    duration_ms: int,
    max_bytes: int = DEFAULT_MAX_STATE_BYTES,
) -> dict[str, Any]:
    truncated_input = truncate_state(input_state, max_bytes=max_bytes)
    truncated_output = truncate_state(output_state, max_bytes=max_bytes)
    return {
        "node": node,
        "input_state": truncated_input,
        "output_state": truncated_output,
        "state": truncated_output,
        "duration_ms": max(0, int(duration_ms)),
    }


def build_node_failed_payload(
    *,
    node: str,
    input_state: dict[str, Any],
    error: str,
    duration_ms: int,
    max_bytes: int = DEFAULT_MAX_STATE_BYTES,
) -> dict[str, Any]:
    return {
        "node": node,
        "input_state": truncate_state(input_state, max_bytes=max_bytes),
        "error": error,
        "duration_ms": max(0, int(duration_ms)),
    }

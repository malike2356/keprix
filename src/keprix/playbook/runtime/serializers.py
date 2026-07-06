"""State serialization helpers."""

from __future__ import annotations

import json
from typing import Any


def serialize_state(state: dict[str, Any]) -> str:
    return json.dumps(state, default=str, sort_keys=True)


def deserialize_state(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Playbook state must deserialize to a dict")
    return data

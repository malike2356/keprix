"""Session trajectory: append-only event log with fork/replay for operators.

Steal the DeepSeek Harness trajectory *idea*. Persist Soft Wall, mutation,
tool, and message events without Cordis. Product modules stay first-class.
"""

from __future__ import annotations

from keprix.trajectory.redaction import redact_payload
from keprix.trajectory.service import TrajectoryService, get_trajectory_service
from keprix.trajectory.store import (
    AppendOnlyViolation,
    TrajectoryStore,
    get_trajectory_store,
    reset_trajectory_store_for_tests,
)
from keprix.trajectory.types import EVENT_TYPES, TrajectoryEvent

__all__ = [
    "AppendOnlyViolation",
    "EVENT_TYPES",
    "TrajectoryEvent",
    "TrajectoryService",
    "TrajectoryStore",
    "get_trajectory_service",
    "get_trajectory_store",
    "redact_payload",
    "reset_trajectory_store_for_tests",
]

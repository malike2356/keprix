"""Background memory review queue for ambient room events (Prompt 45)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class QueuedMemoryCandidate:
    workspace_id: str
    content: str
    source: str = "ambient_room"
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BackgroundReviewQueue:
    def __init__(self) -> None:
        self._queue: dict[str, list[QueuedMemoryCandidate]] = defaultdict(list)

    async def queue_room_memory(self, workspace_id: str, candidates: list[str]) -> None:
        for content in candidates:
            text = content.strip()
            if not text:
                continue
            self._queue[workspace_id].append(
                QueuedMemoryCandidate(workspace_id=workspace_id, content=text)
            )

    def list_pending(self, workspace_id: str) -> list[QueuedMemoryCandidate]:
        return list(self._queue.get(workspace_id, []))

    def clear(self, workspace_id: str | None = None) -> None:
        if workspace_id is None:
            self._queue.clear()
            return
        self._queue.pop(workspace_id, None)


_review_queue: BackgroundReviewQueue | None = None


def get_background_review_queue() -> BackgroundReviewQueue:
    global _review_queue
    if _review_queue is None:
        _review_queue = BackgroundReviewQueue()
    return _review_queue


def reset_background_review_queue() -> BackgroundReviewQueue:
    global _review_queue
    _review_queue = BackgroundReviewQueue()
    return _review_queue

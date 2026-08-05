"""Conversation history deduplication: removes repeated message pairs."""

from __future__ import annotations

from typing import Any


class ContextDeduplicator:
    """Remove exact or near-duplicate messages from conversation history.

    Common in agent loops where the same tool output is sent multiple turns.
    """

    def __init__(self, check_prefix_chars: int = 200) -> None:
        self._prefix_chars = check_prefix_chars

    def deduplicate(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        result: list[dict[str, Any]] = []

        for msg in messages:
            role = str(msg.get("role", ""))
            content = msg.get("content", "")
            if isinstance(content, list):
                content_str = str(content)
            else:
                content_str = str(content or "")

            key = (role, content_str[: self._prefix_chars])
            if key in seen:
                continue
            seen.add(key)
            result.append(msg)

        return result

    def savings(
        self,
        original: list[dict[str, Any]],
        deduplicated: list[dict[str, Any]],
    ) -> int:
        """Number of messages removed."""
        return len(original) - len(deduplicated)

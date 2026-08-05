"""Graceful degradation: tier-level fallback and minimal-response strategy."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DegradeLevel(str, Enum):
    FULL    = "full"       # all tiers healthy
    PARTIAL = "partial"    # some tiers unavailable, best-effort routing
    MINIMAL = "minimal"    # only one tier left; stub responses enabled
    OFFLINE = "offline"    # no tiers available; return cached or error


@dataclass
class DegradeStatus:
    level: DegradeLevel
    available_tiers: list[str]
    failed_tiers: list[str]
    message: str = ""


_STUB_RESPONSE = (
    "I am currently unavailable due to a provider outage. "
    "Please try again in a few moments."
)


class GracefulDegrader:
    """Track which tiers are healthy and decide the current degrade level.

    The engine calls ``mark_tier_failed`` / ``mark_tier_recovered`` as routing
    attempts succeed or fail.  ``current_status`` returns the degrade level so
    callers can decide whether to fall back further or return a stub.
    """

    def __init__(self, all_tier_ids: list[str], stub_response: str = _STUB_RESPONSE) -> None:
        self._all_tiers: list[str] = list(all_tier_ids)
        self._failed: set[str] = set()
        self._stub = stub_response

    # ------------------------------------------------------------------
    # Tier health management
    # ------------------------------------------------------------------

    def mark_tier_failed(self, tier_id: str) -> None:
        self._failed.add(tier_id)
        level = self.current_status().level
        logger.warning("Tier %r failed; degrade level -> %s", tier_id, level)

    def mark_tier_recovered(self, tier_id: str) -> None:
        self._failed.discard(tier_id)
        level = self.current_status().level
        logger.info("Tier %r recovered; degrade level -> %s", tier_id, level)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def current_status(self) -> DegradeStatus:
        available = [t for t in self._all_tiers if t not in self._failed]
        failed    = [t for t in self._all_tiers if t in self._failed]
        n_avail   = len(available)
        n_total   = len(self._all_tiers)

        if n_avail == 0:
            level = DegradeLevel.OFFLINE
            msg   = "All provider tiers unavailable."
        elif n_avail == 1:
            level = DegradeLevel.MINIMAL
            msg   = f"Only tier {available[0]!r} available; minimal mode."
        elif n_avail < n_total:
            level = DegradeLevel.PARTIAL
            msg   = f"{n_avail}/{n_total} tiers available."
        else:
            level = DegradeLevel.FULL
            msg   = "All tiers healthy."

        return DegradeStatus(
            level=level,
            available_tiers=available,
            failed_tiers=failed,
            message=msg,
        )

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def build_stub_message(self, extra: str = "") -> dict[str, Any]:
        """Return an OpenAI-style response dict for offline/minimal mode."""
        content = self._stub
        if extra:
            content = f"{content} ({extra})"
        return {
            "id": "stub",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "_keprix_stub": True,
        }

    def should_stub(self) -> bool:
        return self.current_status().level == DegradeLevel.OFFLINE

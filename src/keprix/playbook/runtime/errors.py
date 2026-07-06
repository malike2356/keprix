"""Playbook runtime exceptions."""

from __future__ import annotations


class PlaybookError(Exception):
    """Base playbook runtime error."""


class PlaybookGraphError(PlaybookError):
    """Invalid graph definition or compilation failure."""


class PlaybookRunError(PlaybookError):
    """Runtime execution failure."""


class PlaybookInterrupt(PlaybookError):
    """Execution paused for human review or approval."""

    def __init__(
        self,
        reason: str,
        *,
        state_patch_schema: dict | None = None,
        approval_request: dict | None = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.state_patch_schema = state_patch_schema
        self.approval_request = approval_request


class PlaybookCancelled(PlaybookError):
    """Run was cancelled by the operator."""


class PlaybookPaused(PlaybookError):
    """Run was paused by the operator."""

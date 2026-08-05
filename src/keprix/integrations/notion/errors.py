"""Notion API error types."""

from __future__ import annotations


class NotionAuthError(Exception):
    """401 / 403: invalid or expired integration token."""


class NotionNotFoundError(Exception):
    """404: page, block, or database not found."""


class NotionRateLimitError(Exception):
    """429: rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = 1) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class NotionValidationError(Exception):
    """400 / 409: bad request or conflict."""


class NotionServerError(Exception):
    """5xx: Notion server error."""


class NotionTimeoutError(Exception):
    """Request timed out."""

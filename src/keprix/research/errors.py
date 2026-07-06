"""Deep research configuration and runtime errors."""

from __future__ import annotations


class ResearchConfigError(RuntimeError):
    """Raised when deep research prerequisites are missing or misconfigured."""


class ResearchPipelineError(RuntimeError):
    """Raised when deep research fails after configuration is valid."""

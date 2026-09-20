"""Seam error types."""

from __future__ import annotations


class SeamError(Exception):
    """Base error for capability seam failures."""


class SeamNotFoundError(SeamError):
    """No active provider (or unknown provider id) for a seam."""


class SeamPolicyDenied(SeamError):
    """Soft Wall / Channel Shield / vault policy blocked a provider call."""

    def __init__(self, message: str, *, error_code: str = "seam_policy_denied"):
        super().__init__(message)
        self.error_code = error_code

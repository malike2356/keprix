"""SSO data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SsoProfile:
    provider: str
    subject: str
    email: str | None
    name: str | None
    avatar_url: str | None


class SsoError(Exception):
    """Base SSO error."""


class InvalidSsoStateError(SsoError):
    """OAuth state validation failed."""


class SsoProviderError(SsoError):
    """Identity provider unreachable or misconfigured."""


class SsoIdentityConflictError(SsoError):
    """Identity already linked to another account."""

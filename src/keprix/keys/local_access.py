"""Runtime access level for a Keprix installation."""

from __future__ import annotations

from keprix.keys.developer_identity import verify_developer_identity


def effective_access_level() -> str:
    """
    Return the effective access level for this host.

    Keprix v1 has no paid feature tiers. Developer mode grants full local access;
    authenticated users otherwise receive standard access with no tier gating.
    """
    if verify_developer_identity():
        return "developer"
    return "standard"

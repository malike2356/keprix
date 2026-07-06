"""Workspace-scoped role checks for slash commands."""

from __future__ import annotations

ROLE_ORDER = ("viewer", "operator", "admin", "owner")


def normalize_role(role: str | None) -> str:
    value = (role or "viewer").strip().lower()
    if value not in ROLE_ORDER:
        return "viewer"
    return value


def role_rank(role: str) -> int:
    try:
        return ROLE_ORDER.index(normalize_role(role))
    except ValueError:
        return 0


def role_allows(user_role: str, min_role: str) -> bool:
    return role_rank(user_role) >= role_rank(min_role)


def default_role_for_channel(channel: str, metadata: dict | None = None) -> str:
    meta = metadata or {}
    if meta.get("role"):
        return normalize_role(str(meta["role"]))
    if channel in {"cli", "tui", "webchat"}:
        return "admin"
    return "viewer"

"""SSO login, link, and user provisioning helpers."""

from __future__ import annotations

import re
import secrets
from typing import Any

from keprix.auth.config import require_approval
from keprix.auth.session import AuthManager, RESERVED_USERNAMES
from keprix.auth.sso.models import SsoProfile
from keprix.auth.sso.store import SsoIdentityStore

_USERNAME_RE = re.compile(r"[^a-z0-9._-]+")


def _unique_username(auth_manager: AuthManager, base: str) -> str:
    cleaned = _USERNAME_RE.sub("", base.strip().lower())[:32]
    if not cleaned or cleaned in RESERVED_USERNAMES:
        cleaned = "user"
    candidate = cleaned
    suffix = 0
    while auth_manager.get_user(candidate):
        suffix += 1
        candidate = f"{cleaned}{suffix}"
    return candidate


def resolve_sso_user(
    auth_manager: AuthManager,
    sso_store: SsoIdentityStore,
    profile: SsoProfile,
    *,
    link_user_id: str | None = None,
) -> dict[str, Any]:
    existing_user_id = sso_store.get_user_id(profile.provider, profile.subject)
    if existing_user_id:
        user = auth_manager.get_user_by_id(existing_user_id)
        if user is None:
            raise ValueError("Linked account no longer exists")
        return user

    if link_user_id:
        user = auth_manager.get_user_by_id(link_user_id)
        if user is None:
            raise ValueError("Account not found")
        sso_store.link(link_user_id, profile)
        _maybe_apply_profile(auth_manager, user, profile)
        return auth_manager.get_user_by_id(link_user_id) or user

    if profile.email:
        matched = auth_manager._find_user_by_login(profile.email)
        if matched:
            sso_store.link(str(matched["id"]), profile)
            _maybe_apply_profile(auth_manager, matched, profile)
            return auth_manager.get_user_by_id(str(matched["id"])) or matched

    username_base = profile.email.split("@", 1)[0] if profile.email else f"{profile.provider}-{profile.subject[:8]}"
    username = _unique_username(auth_manager, username_base)
    password = secrets.token_urlsafe(32)
    user = auth_manager.create_user(
        username,
        password,
        role="user",
        email=profile.email,
        is_approved=not require_approval(),
    )
    sso_store.link(str(user["id"]), profile)
    _maybe_apply_profile(auth_manager, user, profile)
    return auth_manager.get_user_by_id(str(user["id"])) or user


def _maybe_apply_profile(auth_manager: AuthManager, user: dict[str, Any], profile: SsoProfile) -> None:
    updates: dict[str, str | None] = {}
    if profile.name and not user.get("display_name"):
        updates["display_name"] = profile.name
    if profile.avatar_url and not user.get("avatar_url"):
        updates["avatar_url"] = profile.avatar_url
    if profile.email and not user.get("email"):
        updates["email"] = profile.email
    if updates:
        auth_manager.update_profile(str(user["id"]), **updates)

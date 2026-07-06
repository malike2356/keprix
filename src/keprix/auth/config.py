"""Auth configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path


def admin_password() -> str:
    return os.getenv("KEPRIX_ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))


def admin_email() -> str:
    return os.getenv("KEPRIX_ADMIN_EMAIL", os.getenv("ADMIN_EMAIL", "")).strip()


def admin_username() -> str:
    email = admin_email()
    if email:
        return email.lower()
    return "admin"


def multi_user_enabled() -> bool:
    return os.getenv("KEPRIX_MULTI_USER", "false").lower() in {"1", "true", "yes"}


def require_approval() -> bool:
    return os.getenv("KEPRIX_REQUIRE_APPROVAL", "false").lower() in {"1", "true", "yes"}


def session_secret() -> str:
    return os.getenv("SESSION_SECRET", os.getenv("JWT_SECRET", "change-me-in-production"))


def auth_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "true").lower() in {"1", "true", "yes"}


def _writable_data_root(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def data_dir() -> str:
    explicit = os.getenv("KEPRIX_DATA_DIR")
    if explicit:
        return os.path.expanduser(explicit)
    docker_default = Path("/data/keprix")
    if _writable_data_root(docker_default):
        return str(docker_default)
    fallback = Path.home() / ".local" / "share" / "keprix"
    fallback.mkdir(parents=True, exist_ok=True)
    return str(fallback)

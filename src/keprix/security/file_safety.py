"""File write safety rules for keprix tools."""

from __future__ import annotations

import os
from pathlib import Path

from keprix.auth.config import data_dir


def keprix_home() -> Path:
    return Path(os.path.expanduser(os.getenv("KEPRIX_CONFIG_DIR", "~/.keprix")))


def build_write_denied_paths(home: str) -> set[str]:
    root = keprix_home()
    return {
        os.path.realpath(path)
        for path in [
            os.path.join(home, ".ssh", "authorized_keys"),
            os.path.join(home, ".ssh", "id_rsa"),
            os.path.join(home, ".ssh", "id_ed25519"),
            str(root / ".env"),
            str(Path(data_dir()) / ".env"),
            os.path.join(home, ".netrc"),
            os.path.join(home, ".pgpass"),
            "/etc/passwd",
            "/etc/shadow",
        ]
    }


def build_write_denied_prefixes(home: str) -> list[str]:
    return [
        os.path.realpath(path) + os.sep
        for path in [
            os.path.join(home, ".ssh"),
            os.path.join(home, ".aws"),
            os.path.join(home, ".gnupg"),
            os.path.join(home, ".kube"),
        ]
    ]


def get_safe_write_root() -> str | None:
    root = os.getenv("SANDBOX_WRITE_ROOT", os.path.join(data_dir(), "workspace"))
    if not root:
        return None
    return os.path.realpath(os.path.expanduser(root))


def is_write_denied(path: str) -> bool:
    home = os.path.realpath(os.path.expanduser("~"))
    resolved = os.path.realpath(os.path.expanduser(path))
    if resolved in build_write_denied_paths(home):
        return True
    for prefix in build_write_denied_prefixes(home):
        if resolved.startswith(prefix):
            return True
    safe_root = get_safe_write_root()
    if safe_root and not resolved.startswith(safe_root + os.sep) and resolved != safe_root:
        return True
    return False


def assert_write_allowed(path: str) -> None:
    if is_write_denied(path):
        raise PermissionError(f"Write denied for path: {path}")

"""CLI helpers for hot credential rotation."""

from __future__ import annotations

from typing import Any

from keprix.proxy.rotation import write_rotation_signal


def rotate_credential(args: Any) -> dict[str, Any]:
    return write_rotation_signal(args.secret_ref, verify=bool(getattr(args, "verify", False)))

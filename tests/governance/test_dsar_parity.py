"""Tests for governance DSAR and role gate."""

from __future__ import annotations

from fastapi import HTTPException

from keprix.auth.dependencies import require_admin


def test_viewer_denied_admin() -> None:
    try:
        require_admin({"id": "v", "role": "viewer"})
        assert False, "expected 403"
    except HTTPException as exc:
        assert exc.status_code == 403

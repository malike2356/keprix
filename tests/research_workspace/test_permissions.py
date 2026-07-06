"""Permission tests for research workspace."""

from __future__ import annotations

import pytest

from keprix.research_workspace.errors import PermissionDeniedError
from keprix.research_workspace.permissions import assert_can_export, assert_can_read, can_export, can_read


def test_restricted_project_readable_only_by_owner():
    assert can_read(sensitivity_level="restricted", user_id="alice", owner="alice")
    assert not can_read(sensitivity_level="restricted", user_id="bob", owner="alice")


def test_export_denied_by_policy():
    assert not can_export(export_policy="deny", user_id="alice", owner="alice")
    assert can_export(export_policy="deny", user_id="admin", owner="alice", is_admin=True)


def test_assert_can_export_raises():
    with pytest.raises(PermissionDeniedError):
        assert_can_export(export_policy="deny", user_id="alice", owner="alice")

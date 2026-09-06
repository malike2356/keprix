from __future__ import annotations

from pathlib import Path

from keprix.billing.grandfathering import (
    grant_feature_grandfather,
    list_feature_grandfather,
    workspace_has_feature_grandfather,
)


def test_grant_is_idempotent_and_permanent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    assert grant_feature_grandfather("ws", "business_lines", "legacy usage") is True
    assert grant_feature_grandfather("ws", "business_lines", "changed reason") is False
    assert workspace_has_feature_grandfather("ws", "business_lines") is True
    assert list_feature_grandfather("ws")["business_lines"]["reason"] == "legacy usage"

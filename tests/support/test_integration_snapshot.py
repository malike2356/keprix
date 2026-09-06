"""Support integration snapshot tests."""

from pathlib import Path

from keprix.crm.store import reset_crm_store_for_tests
from keprix.support.integration_snapshot import workspace_integration_snapshot


def test_snapshot_is_complete_and_disconnected_is_not_an_error(tmp_path: Path):
    store = reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    snapshot = workspace_integration_snapshot("ws-a", store=store)
    names = {item["integration"] for item in snapshot["items"]}
    assert names == {"telegram", "email", "google", "calendar", "whatsapp", "linkedin", "meta", "x", "workers", "domains"}
    assert all(item["status"] == "disconnected" for item in snapshot["items"])


def test_snapshot_does_not_cross_workspace(tmp_path: Path):
    store = reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    snapshot = workspace_integration_snapshot("ws-b", store=store)
    assert snapshot["workspace_id"] == "ws-b"
    assert all(not any(row.get("configured") for row in item["details"]) for item in snapshot["items"])

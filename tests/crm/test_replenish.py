"""Replenishment trigger tests."""

from pathlib import Path

import pytest

from keprix.crm.replenish import MAX_REPLENISH_COUNT, trigger_replenish
from keprix.crm.store import reset_crm_store_for_tests
from keprix.discovery import reset_discovery_registry_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    reset_discovery_registry_for_tests()
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_trigger_uses_ratio_and_is_idempotent(store):
    store.upsert_replenish_settings("ws-a", ratio=1.5)
    first = trigger_replenish("ws-a", "batch-1", 3, store=store)
    second = trigger_replenish("ws-a", "batch-1", 3, store=store)

    assert first["enqueued_count"] == 5
    assert first["job"]["params"]["params"]["replenish"] is True
    assert first["job"]["params"]["auto_materialize"] is True
    assert second["idempotent"] is True
    assert len(store.list_replenish_events("ws-a")) == 1


def test_trigger_caps_work_and_preserves_workspace_isolation(store):
    result = trigger_replenish("ws-a", "same-batch", 100000, store=store)
    assert result["enqueued_count"] == MAX_REPLENISH_COUNT
    other = trigger_replenish("ws-b", "same-batch", 2, store=store)
    assert other["idempotent"] is False
    assert len(store.list_replenish_events("ws-a")) == 1
    assert len(store.list_replenish_events("ws-b")) == 1


def test_negative_inputs_and_ratio_are_rejected(store):
    with pytest.raises(ValueError, match="sent_count"):
        trigger_replenish("ws", "bad", -1, store=store)
    with pytest.raises(ValueError, match="replenish_ratio"):
        store.upsert_replenish_settings("ws", ratio=-0.1)


def test_zero_sent_count_does_not_create_a_discovery_job(store):
    result = trigger_replenish("ws", "empty-batch", 0, store=store)
    assert result["event"]["status"] == "done"
    assert store.list_discovery_jobs("ws") == []

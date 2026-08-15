from pathlib import Path

from keprix.crm.channel_pacing import can_send, drain_batch, record_send, sent_today
from keprix.crm.store import reset_crm_store_for_tests


def test_channel_caps_are_independent_and_failed_send_does_not_consume_quota(tmp_path: Path) -> None:
    store = reset_crm_store_for_tests(tmp_path / "pacing.sqlite")
    assert drain_batch(store, "ws_a", "email", ["1", "2", "3"], 2) == ["1", "2"]
    assert record_send(store, "ws_a", "email", "1")
    assert record_send(store, "ws_a", "email", "2")
    assert not can_send(store, "ws_a", "email", 2)
    assert can_send(store, "ws_a", "linkedin", 2)
    assert sent_today(store, "ws_a", "email") == 2
    assert drain_batch(store, "ws_a", "email", ["1", "2", "3"], 2) == []

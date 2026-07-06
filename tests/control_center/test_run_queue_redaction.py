"""Failed run log redaction test (Prompt 61)."""

from __future__ import annotations

from keprix.control_center.run_queue import enqueue_run, fail_run
from keprix.control_center.store import ControlCenterStore, reset_control_center_store


def test_failed_run_redacts_secrets_in_logs(tmp_path):
    reset_control_center_store(ControlCenterStore(base_dir=tmp_path / "control_center"))
    run = enqueue_run(payload={"playbook_id": "demo"})
    failed = fail_run(
        run["id"],
        logs=["Error: api_key=sk-secret12345678901234567890 failed"],
    )
    assert failed is not None
    assert failed["status"] == "failed"
    assert "sk-secret" not in failed["logs"][0]
    assert "REDACTED" in failed["logs"][0]

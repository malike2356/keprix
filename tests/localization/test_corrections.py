"""Prompt 50 correction workflow tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.backend.localization.audit import get_audit_service
from keprix.backend.localization.corrections import get_correction_queue
from keprix.backend.localization.corrections_store import CorrectionsStore, reset_corrections_store
from keprix.backend.localization.flywheel import get_flywheel, get_quality_metrics
from keprix.backend.localization.glossary import get_glossary_service
from keprix.backend.localization.schemas import LocalizationAuditRecord
from keprix.backend.localization.store import LocalizationStore, reset_localization_store
from keprix.backend.localization.translation import translate_text


@pytest.fixture
def flywheel_env(tmp_path, monkeypatch):
    loc_dir = tmp_path / "localization"
    fly_dir = loc_dir / "flywheel"
    fly_dir.mkdir(parents=True)
    loc_store = LocalizationStore(base_dir=loc_dir)
    corr_store = CorrectionsStore(base_dir=fly_dir)
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_localization_store()
    reset_corrections_store()
    monkeypatch.setattr("keprix.backend.localization.store.get_localization_store", lambda: loc_store)
    monkeypatch.setattr("keprix.backend.localization.corrections_store.get_corrections_store", lambda: corr_store)
    monkeypatch.setattr("keprix.backend.localization.audit.get_localization_store", lambda: loc_store)
    import keprix.backend.localization.audit as audit_module
    import keprix.backend.localization.corrections as corrections_module
    import keprix.backend.localization.flywheel as flywheel_module

    audit_module._audit_service = None
    corrections_module._queue = None
    flywheel_module._flywheel = None
    flywheel_module._metrics = None
    from keprix.backend.notifications.store import reset_notification_store
    import keprix.backend.notifications.inbox as inbox_module

    reset_notification_store()
    inbox_module._service = None
    return {"loc_store": loc_store, "corr_store": corr_store, "tmp_path": tmp_path}


async def _seed_audit(workspace_id: str = "ws-fly") -> str:
    audit = await get_audit_service().write(
        LocalizationAuditRecord(
            workspace_id=workspace_id,
            channel="webchat",
            request_id="req-1",
            input_type="text",
            original_text="Me pɛ borehole",
            translated_input="I want a borehole",
            final_response="Please share GPS location",
            detected_language="ak-GH",
            output_language="ak-GH",
            detection_confidence=0.8,
            translation_provider="local",
        )
    )
    return str(audit["id"])


@pytest.mark.asyncio
async def test_user_correction_creates_pending_and_inbox(flywheel_env) -> None:
    audit_id = await _seed_audit()
    record = await get_correction_queue().submit_user_correction(
        audit_record_id=audit_id,
        correction_type="translation",
        original_value="I want a borehole",
        corrected_value="I need a borehole",
        workspace_id="ws-fly",
        source_language="ak-GH",
        target_language="en-GH",
        domain="borehole_drilling",
    )
    assert record.status == "pending"
    inbox = flywheel_env["tmp_path"] / "notifications" / "ws-fly" / "notifications.jsonl"
    assert inbox.exists()
    assert "localization_correction" in inbox.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_operator_auto_approve_applies_translation_override(flywheel_env) -> None:
    audit_id = await _seed_audit()
    await get_correction_queue().submit_operator_correction(
        audit_record_id=audit_id,
        correction_type="translation",
        original_value="yield test",
        corrected_value="yield test",
        workspace_id="ws-fly",
        operator_user_id="op-1",
        source_language="ak-GH",
        target_language="en-GH",
        domain="borehole_drilling",
    )
    result = await translate_text(
        workspace_id="ws-fly",
        text="yield test",
        source_language="ak-GH",
        target_language="en-GH",
    )
    assert result.provider == "override_cache"
    assert result.translated_text == "yield test"


@pytest.mark.asyncio
async def test_glossary_addition_updates_glossary(flywheel_env) -> None:
    audit_id = await _seed_audit()
    await get_correction_queue().submit_operator_correction(
        audit_record_id=audit_id,
        correction_type="glossary_addition",
        original_value="nsuo abɔdem",
        corrected_value="water pressure test",
        workspace_id="ws-fly",
        operator_user_id="op-1",
        source_language="ak-GH",
        target_language="en-GH",
        domain="borehole_drilling",
        auto_approve=True,
    )
    glossary = get_glossary_service().get("borehole_drilling_v1")
    assert glossary is not None
    terms = [entry["term"] for entry in glossary["entries"]]
    assert "nsuo abɔdem" in terms


@pytest.mark.asyncio
async def test_training_sample_created_on_approval(flywheel_env) -> None:
    audit_id = await _seed_audit()
    record = await get_correction_queue().submit_operator_correction(
        audit_record_id=audit_id,
        correction_type="transcription",
        original_value="wrong transcript",
        corrected_value="Me pɛ borehole",
        workspace_id="ws-fly",
        operator_user_id="op-1",
        source_language="ak-GH",
        domain="borehole_drilling",
    )
    assert record.staged_for_training is True
    assert record.training_sample_id


@pytest.mark.asyncio
async def test_export_sm4t_marks_samples_exported(flywheel_env, tmp_path) -> None:
    audit_id = await _seed_audit()
    await get_correction_queue().submit_operator_correction(
        audit_record_id=audit_id,
        correction_type="translation",
        original_value="Hello",
        corrected_value="Akwaaba",
        workspace_id="ws-fly",
        operator_user_id="op-1",
        source_language="en-GH",
        target_language="ak-GH",
        domain="borehole_drilling",
    )
    out_dir = tmp_path / "export"
    summary = await get_flywheel().export_sm4t_training_data(out_dir, workspace_id="ws-fly")
    assert summary.total_samples >= 1
    assert (out_dir / "manifest.json").exists()
    second = await get_flywheel().export_sm4t_training_data(out_dir / "second", workspace_id="ws-fly")
    assert second.total_samples == 0


@pytest.mark.asyncio
async def test_intent_corrections_export_separately(flywheel_env, tmp_path) -> None:
    audit_id = await _seed_audit()
    await get_correction_queue().submit_operator_correction(
        audit_record_id=audit_id,
        correction_type="intent",
        original_value='{"intent":"quote"}',
        corrected_value='{"intent":"site_assessment"}',
        workspace_id="ws-fly",
        operator_user_id="op-1",
        source_language="ak-GH",
        domain="borehole_drilling",
    )
    out_dir = tmp_path / "llm-export"
    sm4t = await get_flywheel().export_sm4t_training_data(out_dir, workspace_id="ws-fly")
    llm = await get_flywheel().export_llm_correction_data(out_dir, workspace_id="ws-fly")
    assert sm4t.total_samples == 0
    assert llm["intent_entity_corrections"] >= 1
    assert (out_dir / "intent_entity_corrections.jsonl").exists()


@pytest.mark.asyncio
async def test_provider_accuracy_populated_after_correction(flywheel_env) -> None:
    audit_id = await _seed_audit()
    await get_correction_queue().submit_operator_correction(
        audit_record_id=audit_id,
        correction_type="translation",
        original_value="bad",
        corrected_value="good",
        workspace_id="ws-fly",
        operator_user_id="op-1",
        source_language="ak-GH",
        target_language="en-GH",
        domain="borehole_drilling",
    )
    metrics = await get_quality_metrics().get_provider_accuracy_by_language("ws-fly")
    assert metrics["providers"]


@pytest.mark.asyncio
async def test_reject_requires_reason_via_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "false")
    from httpx import ASGITransport, AsyncClient

    from keprix.api.main import app

    flywheel_env  # noqa: ensure fixture ordering if composed later
    audit_id = await _seed_audit("ws-api")
    submit = await get_correction_queue().submit_user_correction(
        audit_record_id=audit_id,
        correction_type="translation",
        original_value="a",
        corrected_value="b",
        workspace_id="ws-api",
        source_language="ak-GH",
        target_language="en-GH",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        bad = await client.post(
            f"/api/localization/corrections/{submit.id}/reject",
            json={"reason": ""},
        )
        assert bad.status_code == 422

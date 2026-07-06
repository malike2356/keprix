"""Ghana borehole example flow (Prompt 27 acceptance)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import yaml
from pathlib import Path

from keprix.backend.gateway.language_middleware import InboundMessage, process_inbound_message
from keprix.backend.localization.schemas import TranscriptionResult, TranscriptSegment, TranslationResult
from keprix.backend.playbook.localization import GHANA_BOREHOLE_PLAYBOOK, PlaybookLocalizationMeta


@pytest.mark.asyncio
async def test_borehole_voice_note_intake_flow(isolated_store) -> None:
    transcription = TranscriptionResult(
        language_code="ak-GH",
        transcript="Me pɛ borehole wɔ Kumasi",
        confidence=0.88,
        segments=[TranscriptSegment(start=0.0, end=2.4, text="Me pɛ borehole wɔ Kumasi", confidence=0.88)],
        provider="whisper",
    )
    inbound_translation = TranslationResult(
        source_language="ak-GH",
        target_language="en-GH",
        source_text=transcription.transcript,
        translated_text="I want a borehole in Kumasi",
        confidence=0.86,
        glossary_matches=["borehole"],
        warnings=[],
        provider="local",
    )
    outbound_translation = TranslationResult(
        source_language="en-GH",
        target_language="ak-GH",
        source_text="Please share your community name and GPS location.",
        translated_text="Fa wo community din ne GPS location ma me.",
        confidence=0.82,
        glossary_matches=[],
        warnings=[],
        provider="local",
    )

    with patch(
        "keprix.backend.gateway.language_middleware.transcribe_audio",
        new=AsyncMock(return_value=transcription),
    ), patch(
        "keprix.backend.gateway.language_middleware.translate_text",
        new=AsyncMock(side_effect=[inbound_translation, outbound_translation]),
    ), patch(
        "keprix.backend.gateway.language_middleware.synthesize_speech",
        new=AsyncMock(return_value=None),
    ):
        result = await process_inbound_message(
            InboundMessage(
                workspace_id="ws-borehole",
                channel="whatsapp",
                user_id="farmer-1",
                audio_bytes=b"fake-audio",
                glossary_id=GHANA_BOREHOLE_PLAYBOOK.glossary_id,
                domain=GHANA_BOREHOLE_PLAYBOOK.domain,
                workspace_response="Please share your community name and GPS location.",
            )
        )

    assert result.detected_language == "ak-GH"
    assert "Kumasi" in result.translated_input or "borehole" in result.translated_input.lower()
    assert result.translated_response
    assert result.audit_id


def test_playbook_yaml_matches_runtime_metadata() -> None:
    raw = yaml.safe_load(Path("examples/borehole-ghana/playbook.yaml").read_text(encoding="utf-8"))
    playbook = PlaybookLocalizationMeta.from_metadata(raw)
    assert playbook.playbook_id == "ghana-borehole-advisor"
    assert playbook.glossary_id == GHANA_BOREHOLE_PLAYBOOK.glossary_id
    assert playbook.human_review_below_confidence == 0.72

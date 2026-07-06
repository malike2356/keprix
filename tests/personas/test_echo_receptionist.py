"""Tests for ECHO receptionist module."""

from __future__ import annotations

import pytest

from keprix.personas.echo.knowledge import BusinessProfile
from keprix.personas.echo.receptionist import EchoReceptionist, EscalationType
from keprix.security.vault_service import reset_vault_service


@pytest.fixture
def receptionist() -> EchoReceptionist:
    profile = BusinessProfile(business_name="Acme Ltd")
    return EchoReceptionist(workspace_id="ws-echo", user_id="user-echo", profile=profile)


@pytest.fixture(autouse=True)
def reset_vault() -> None:
    reset_vault_service()
    yield
    reset_vault_service()


def test_greeting_uses_business_name(receptionist: EchoReceptionist) -> None:
    greeting = receptionist.greeting()
    assert "Acme Ltd" in greeting
    assert "ECHO" in greeting


def test_detect_emergency_escalation(receptionist: EchoReceptionist) -> None:
    assert receptionist.detect_escalation("This is a medical emergency") == EscalationType.EMERGENCY


def test_detect_legal_escalation(receptionist: EchoReceptionist) -> None:
    assert receptionist.detect_escalation("I will sue you and contact my solicitor") == EscalationType.LEGAL


def test_parse_twilio_webhook(receptionist: EchoReceptionist) -> None:
    parsed = receptionist.parse_voice_webhook(
        {"CallSid": "CA123", "From": "+441234567890", "SpeechResult": "I want to book a meeting"}
    )
    assert parsed["call_id"] == "CA123"
    assert parsed["caller_phone"] == "+441234567890"
    assert parsed["speech"] == "I want to book a meeting"


@pytest.mark.asyncio
async def test_inbound_webhook_greets_on_empty_speech(receptionist: EchoReceptionist) -> None:
    turn = await receptionist.handle_inbound_webhook({"CallSid": "CA-greet", "From": "+44111"})
    assert "Acme Ltd" in turn.reply
    assert turn.action == "greet"
    assert turn.metadata["voice"]["ring_within_seconds"] == 12


@pytest.mark.asyncio
async def test_emergency_call_escalates(receptionist: EchoReceptionist) -> None:
    turn = await receptionist.handle_inbound_webhook(
        {"CallSid": "CA-emergency", "From": "+44222", "SpeechResult": "Someone is hurt, call an ambulance"}
    )
    assert turn.escalation == EscalationType.EMERGENCY
    assert "999" in turn.reply
    assert turn.action == "escalate_emergency"


@pytest.mark.asyncio
async def test_legal_threat_flags_warden(receptionist: EchoReceptionist) -> None:
    turn = await receptionist.handle_inbound_webhook(
        {"CallSid": "CA-legal", "From": "+44333", "SpeechResult": "I am starting a lawsuit"}
    )
    assert turn.escalation == EscalationType.LEGAL
    assert turn.metadata.get("flag_warden") is True


@pytest.mark.asyncio
async def test_booking_intent_offers_slots(receptionist: EchoReceptionist) -> None:
    turn = await receptionist.handle_inbound_webhook(
        {
            "CallSid": "CA-book",
            "From": "+44444",
            "SpeechResult": "My name is Jane Smith. I would like to book an appointment.",
        }
    )
    assert turn.action in {"offer_slots", "booking_unavailable", "identify"}
    if turn.action == "offer_slots":
        assert "available" in turn.reply.lower()


@pytest.mark.asyncio
async def test_store_call_recording_encrypted(receptionist: EchoReceptionist) -> None:
    result = await receptionist.store_call_recording(b"audio-bytes", call_id="CA-rec")
    assert result["encrypted"] is True
    assert result["vault_item_id"]

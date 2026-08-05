from keprix.voice.escalation import EscalationEngine, EscalationPolicy


def test_escalation_engine_detects_human_and_duration() -> None:
    engine = EscalationEngine(EscalationPolicy(transfer_to="+155501", max_duration_seconds=60))

    assert engine.should_escalate("can I speak to a human")
    assert engine.should_escalate("normal call", duration_seconds=61)
    assert not engine.should_escalate("can I book tomorrow?", duration_seconds=10)
    assert "connect" in engine.handoff_message()

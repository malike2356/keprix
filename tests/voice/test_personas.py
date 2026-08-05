from keprix.voice.personas.receptionist import AIVA_RECEPTIONIST_PROMPT, receptionist_greeting, should_escalate


def test_receptionist_persona_is_aiva_branded() -> None:
    assert "You are Aiva" in AIVA_RECEPTIONIST_PROMPT
    assert "Aiva speaking" in receptionist_greeting("Acme")


def test_receptionist_escalation_triggers() -> None:
    assert should_escalate("I need a human right now")
    assert should_escalate("This is an emergency")
    assert should_escalate("I am going to sue")
    assert not should_escalate("Can I book a viewing tomorrow?")

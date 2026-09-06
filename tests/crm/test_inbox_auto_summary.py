from keprix.crm import engagement


def test_inbox_summary_uses_shared_email_llm(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    async def fake_summary(subject, body, sender):
        assert subject == "Question"
        assert body == "Can we chat tomorrow?"
        assert sender == "person@example.test"
        return {"summary": "The sender asks to schedule a chat tomorrow.", "tags": ["chat"]}

    monkeypatch.setattr("keprix.email.llm.summarize_email", fake_summary)
    summary, intent = engagement._inbox_summary("Question", "Can we chat tomorrow?", "person@example.test")
    assert summary == "The sender asks to schedule a chat tomorrow."
    assert intent == "chat"


def test_inbox_summary_failure_keeps_empty_summary_and_fallback_intent(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    async def fail(*_args):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("keprix.email.llm.summarize_email", fail)
    assert engagement._inbox_summary("", "Please unsubscribe", "person@example.test") == ("", "noise")

from keprix.providers.fallback.circuit_breaker import CircuitBreaker


def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker(threshold=2, cooldown_seconds=60)

    assert breaker.allow("groq")
    assert not breaker.record_failure("groq")
    assert breaker.record_failure("groq")
    assert not breaker.allow("groq")

    breaker.record_success("groq")
    assert breaker.allow("groq")

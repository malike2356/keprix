import pytest

from keprix.providers.combo.engine import ComboEngine
from keprix.providers.combo.tier import ComboTier, ProviderCandidate, ProviderCombo


@pytest.mark.asyncio
async def test_combo_engine_falls_back_to_next_provider() -> None:
    async def failing(**kwargs):
        raise RuntimeError("503 upstream")

    async def working(**kwargs):
        return {"text": "ok", "usage": {"total_tokens": 12}}

    combo = ProviderCombo(
        id="default",
        name="Default",
        tiers=[ComboTier(id="api_keys", name="API", providers=[ProviderCandidate("bad"), ProviderCandidate("good")])],
    )
    engine = ComboEngine({"default": combo}, {"bad": failing, "good": working})

    result = await engine.route([{"role": "user", "content": "hello"}], estimated_tokens=5)

    assert result.response["text"] == "ok"
    assert result.provider == "good"
    assert [attempt.provider for attempt in result.explanation.attempts] == ["bad", "good"]
    assert result.explanation.selected_provider == "good"


@pytest.mark.asyncio
async def test_combo_engine_skips_providers_without_quota() -> None:
    async def working(**kwargs):
        return {"text": kwargs["provider"]}

    combo = ProviderCombo(
        id="default",
        name="Default",
        tiers=[ComboTier(id="free", name="Free", providers=[ProviderCandidate("empty"), ProviderCandidate("full")])],
    )
    engine = ComboEngine({"default": combo}, {"empty": working, "full": working})
    await engine.quota.set_limit("empty", 10)
    await engine.quota.record_usage("empty", 10)
    await engine.quota.set_limit("full", 100)

    result = await engine.route([{"role": "user", "content": "hello"}], estimated_tokens=20)

    assert result.provider == "full"


@pytest.mark.asyncio
async def test_combo_engine_explanation_reports_missing_handler() -> None:
    async def working(**kwargs):
        return {"text": "ok"}

    combo = ProviderCombo(
        id="default",
        name="Default",
        tiers=[ComboTier(id="fallback", name="Fallback", providers=[ProviderCandidate("missing"), ProviderCandidate("ollama")])],
    )
    engine = ComboEngine({"default": combo}, {"ollama": working})

    result = await engine.route([])

    assert result.provider == "ollama"
    assert result.explanation.attempts[0].status == "skipped"
    assert result.explanation.attempts[0].reason == "provider handler missing"

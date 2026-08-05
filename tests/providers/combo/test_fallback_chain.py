import pytest

from keprix.providers.fallback.chain import FallbackChain


@pytest.mark.asyncio
async def test_fallback_chain_returns_first_success() -> None:
    async def bad(**kwargs):
        raise RuntimeError("down")

    async def good(**kwargs):
        return "ok"

    assert await FallbackChain({"bad": bad, "good": good}).execute(["bad", "good"]) == "ok"

import pytest

from keprix.providers.quota.fair_share import FairShareAllocator
from keprix.providers.quota.tracker import QuotaTracker


@pytest.mark.asyncio
async def test_fair_share_chooses_account_with_most_remaining_ratio() -> None:
    quota = QuotaTracker()
    await quota.set_limit("openai", 100, account_id="a")
    await quota.set_limit("openai", 100, account_id="b")
    await quota.record_usage("openai", 80, account_id="a")
    allocator = FairShareAllocator(quota)

    assert await allocator.choose_account("openai", ["a", "b"], estimated_tokens=10) == "b"

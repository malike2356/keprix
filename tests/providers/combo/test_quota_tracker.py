import pytest

from keprix.providers.quota.tracker import QuotaTracker


@pytest.mark.asyncio
async def test_quota_tracker_checks_reserves_and_predicts_exhaustion() -> None:
    quota = QuotaTracker()
    await quota.set_limit("deepseek", 100)

    assert await quota.check("deepseek", 80)
    assert await quota.reserve("deepseek", 20)
    assert not await quota.check("deepseek", 90)

    await quota.record_usage("deepseek", 20)
    bucket = await quota.get_bucket("deepseek")
    assert bucket.used == 20
    assert bucket.reserved == 0
    assert await quota.predict_exhaustion("deepseek") is not None

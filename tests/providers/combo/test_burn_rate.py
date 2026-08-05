import pytest

from keprix.providers.quota.burn_rate import BurnRateMonitor
from keprix.providers.quota.saturation import SaturationMonitor
from keprix.providers.quota.tracker import QuotaTracker


@pytest.mark.asyncio
async def test_burn_rate_and_saturation_signal() -> None:
    quota = QuotaTracker()
    await quota.set_limit("groq", 100)
    bucket = await quota.get_bucket("groq")
    bucket.burn_rate = 10
    await quota.record_usage("groq", 95)

    seconds = await BurnRateMonitor(quota).seconds_until_empty("groq")
    signal = await SaturationMonitor(quota).check("groq")

    assert seconds is not None
    assert signal.level == "critical"

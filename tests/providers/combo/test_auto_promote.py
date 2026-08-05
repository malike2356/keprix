import pytest

from keprix.providers.combo.auto_promote import AutoPromoter
from keprix.providers.combo.health import HealthMonitor
from keprix.providers.combo.tier import ComboTier, ProviderCandidate
from keprix.providers.quota.tracker import QuotaTracker


@pytest.mark.asyncio
async def test_auto_promote_orders_by_health_and_quota() -> None:
    quota = QuotaTracker()
    health = HealthMonitor()
    promoter = AutoPromoter(health, quota)
    tier = ComboTier(id="api", name="API", providers=[ProviderCandidate("slow"), ProviderCandidate("fast")])
    health.record_success("fast", 100)
    health.record_success("slow", 5000)
    await quota.set_limit("fast", 100)
    await quota.set_limit("slow", 100)

    ordered = await promoter.order(tier, estimated_tokens=10)

    assert [candidate.provider_id for candidate in ordered] == ["fast", "slow"]

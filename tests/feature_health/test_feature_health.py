"""Tests for feature health audit and build gate."""

from __future__ import annotations

from keprix.feature_health import (
    FeatureRegistry,
    can_build_new_feature,
    check_all_features,
    evaluate_build_gate,
    generate_fix_queue,
    prioritize_fixes,
    traffic_light,
)


def test_smoke_and_priorities() -> None:
    reg = FeatureRegistry()
    reg.register("billing", ["/api/billing"], "billing", critical_path=True, revenue_impact=10)
    reg.register("crm", ["/api/crm"], "growth")
    reg.register("legacy", ["/api/legacy"], "ops")
    reg.register("slow", ["/api/slow"], "platform")

    def fetch(url: str) -> tuple[int, bool]:
        if "slow" in url:
            return 200, True
        return 503, False

    check_all_features(
        registry=reg,
        base_url="http://example.test",
        fetch_fn=fetch,
        get_error_rate=lambda name: 0.02 if name == "slow" else 0.0,
        get_usage=lambda name: (
            {"active_users_7d": 5, "adoption_rate": 20}
            if name in {"billing", "crm"}
            else {"active_users_7d": 0, "adoption_rate": 0}
        ),
    )

    queue = prioritize_fixes(reg.get_all())
    assert [i.priority for i in queue] == ["P0", "P1", "P2", "P3"]
    assert queue[0].feature == "billing"
    packed = generate_fix_queue(reg.get_all())
    assert any(d.feature == "legacy" for d in packed["deprecate"])
    assert traffic_light("broken") == "red"


def test_build_gate_blocks_p0() -> None:
    reg = FeatureRegistry()
    reg.register("auth", ["/auth"], "security", critical_path=True)
    check_all_features(
        registry=reg,
        base_url="http://example.test",
        fetch_fn=lambda _u: (500, False),
        get_usage=lambda _n: {"active_users_7d": 3, "adoption_rate": 10},
    )
    assert can_build_new_feature(reg) is False
    gate = evaluate_build_gate(reg)
    assert gate["blocked"] is True
    assert gate["blocking_issues"][0]["feature"] == "auth"


def test_p3_does_not_block_build() -> None:
    reg = FeatureRegistry()
    reg.register("dead", ["/dead"], "ops")
    check_all_features(
        registry=reg,
        base_url="http://example.test",
        fetch_fn=lambda _u: (404, False),
        get_usage=lambda _n: {"active_users_7d": 0, "adoption_rate": 0},
    )
    assert can_build_new_feature(reg) is True
    gate = evaluate_build_gate(reg)
    assert gate["allowed"] is True
    assert gate["deprecate"][0]["feature"] == "dead"

from keprix.providers.combo.builder import build_combos


def test_build_combos_loads_default_and_extends_parent() -> None:
    combos = build_combos()

    assert "default" in combos
    assert "petraclus_default" in combos
    assert combos["default"].tiers[0].providers[0].provider_id == "kiro"
    assert any(tier.id == "fallback" for tier in combos["petraclus_default"].tiers)

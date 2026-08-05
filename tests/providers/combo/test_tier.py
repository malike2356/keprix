from keprix.providers.combo.tier import ComboTier, ProviderCombo


def test_combo_tier_parses_string_and_mapping_providers() -> None:
    tier = ComboTier.from_config(
        {
            "id": "api_keys",
            "providers": ["deepseek", {"id": "openai", "model": "gpt-4.1-mini", "account_id": "team-a", "weight": 2}],
        }
    )

    assert tier.id == "api_keys"
    assert tier.providers[0].provider_id == "deepseek"
    assert tier.providers[1].provider_id == "openai"
    assert tier.providers[1].model == "gpt-4.1-mini"
    assert tier.providers[1].account_id == "team-a"


def test_provider_combo_parses_tiers() -> None:
    combo = ProviderCombo.from_config({"id": "default", "tiers": [{"id": "fallback", "providers": ["ollama"]}]})

    assert combo.id == "default"
    assert combo.tiers[0].providers[0].provider_id == "ollama"

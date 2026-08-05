"""Build provider combos from YAML config."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.providers.combo.tier import ProviderCombo


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "combos.yaml"


def load_combo_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    try:
        import yaml
    except Exception as exc:
        raise RuntimeError("PyYAML is required to load provider combo config") from exc
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Combo config must be a mapping")
    return data


def build_combos(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, ProviderCombo]:
    data = load_combo_config(path)
    combos = {combo.id: combo for combo in (ProviderCombo.from_config(raw) for raw in data.get("combos", []))}
    for combo in list(combos.values()):
        if not combo.extends:
            continue
        parent = combos.get(combo.extends)
        if parent is None:
            raise ValueError(f"Combo {combo.id} extends unknown combo {combo.extends}")
        combo.tiers = _merge_tiers(parent, combo)
    return combos


def _merge_tiers(parent: ProviderCombo, child: ProviderCombo) -> list:
    by_id = {tier.id: tier for tier in parent.tiers}
    for tier in child.tiers:
        by_id[tier.id] = tier
    return list(by_id.values())

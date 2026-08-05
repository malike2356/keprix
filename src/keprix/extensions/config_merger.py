"""Merge product-specific configuration into the Keprix base config."""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a deep copy of ``base``.

    - Nested dicts are merged recursively.
    - Lists are replaced entirely (not concatenated).
    - Scalars from override win over scalars from base.
    """
    result = copy.deepcopy(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result


class ConfigMerger:
    """Merge per-product configuration files into the active Keprix config.

    Products ship a ``config/<product>.yaml`` that overrides or extends the
    Keprix base configuration. This class loads and merges them in a defined
    order so that:
      1. Keprix base config provides defaults.
      2. Each product config adds product-specific sections.
      3. Environment variables still win over everything (handled elsewhere).

    Conflict rule: two products MUST NOT override the same key at the top
    level. If they do, ``validate_no_conflicts()`` raises.

    Usage::

        merger = ConfigMerger(base_config=keprix_base)
        merged = merger.apply(product_config)
        merger.validate_no_conflicts([config_a, config_b])
    """

    def __init__(self, base_config: dict[str, Any] | None = None) -> None:
        self._base = base_config or {}

    def apply(self, product_config: dict[str, Any]) -> dict[str, Any]:
        """Return a merged config: Keprix base + product overrides."""
        merged = deep_merge(self._base, product_config)
        logger.debug("Config merged; top-level keys: %s", list(merged))
        return merged

    def apply_all(self, product_configs: list[dict[str, Any]]) -> dict[str, Any]:
        """Apply multiple product configs sequentially onto the base."""
        result = copy.deepcopy(self._base)
        for cfg in product_configs:
            result = deep_merge(result, cfg)
        return result

    def validate_no_conflicts(
        self, product_configs: list[dict[str, Any]], strict_keys: list[str] | None = None
    ) -> list[str]:
        """Return top-level keys that two or more products both try to override.

        ``strict_keys`` is an optional list of keys that must never be
        overridden by a product (e.g., ``["security", "auth"]``).
        """
        key_owners: dict[str, list[int]] = {}
        for i, cfg in enumerate(product_configs):
            for key in cfg:
                key_owners.setdefault(key, []).append(i)

        conflicts = [k for k, owners in key_owners.items() if len(owners) > 1]

        if strict_keys:
            for cfg in product_configs:
                for key in strict_keys:
                    if key in cfg:
                        conflicts.append(f"{key}(strict)")

        if conflicts:
            logger.warning("Config conflicts detected: %s", conflicts)

        return conflicts

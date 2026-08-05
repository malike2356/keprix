"""Discover Keprix features introduced in each release version."""

from __future__ import annotations

from dataclasses import dataclass, field

from .versions import version_gt, version_lte, version_tuple


@dataclass
class FeatureInfo:
    """A Keprix capability introduced in a specific release."""
    name: str
    description: str
    module: str
    version: str
    requires_config: bool = False
    breaking: bool = False
    migration_guide: str | None = None
    prompt_name: str | None = None


# Registry of features shipped per Keprix version (cross-product upgrade discovery).
FEATURE_REGISTRY: dict[str, list[FeatureInfo]] = {
    "0.4.0": [
        FeatureInfo(
            name="billing",
            description="Native SaaS billing with Stripe integration",
            module="keprix.billing",
            version="0.4.0",
            requires_config=True,
            prompt_name="adopt-billing",
        ),
        FeatureInfo(
            name="governance",
            description="Generic governance layer (scout/ renamed to governance/)",
            module="keprix.governance",
            version="0.4.0",
            breaking=True,
            migration_guide="migrations/upgrade/0.4.0-scout-to-governance.md",
        ),
    ],
    "0.5.0": [
        FeatureInfo(
            name="combo_routing",
            description="Smart provider routing with combos, quota, and auto-fallback",
            module="keprix.providers.combo",
            version="0.5.0",
            requires_config=True,
            prompt_name="adopt-routing",
        ),
        FeatureInfo(
            name="compression",
            description="RTK + Caveman token compression",
            module="keprix.providers.compression",
            version="0.5.0",
            requires_config=False,
            prompt_name="adopt-cache",
        ),
        FeatureInfo(
            name="guardrails",
            description="PII masking and prompt injection defence",
            module="keprix.providers.guardrails",
            version="0.5.0",
            requires_config=False,
        ),
        FeatureInfo(
            name="a2a",
            description="Agent-to-Agent protocol and task management",
            module="keprix.providers.a2a",
            version="0.5.0",
            requires_config=False,
            prompt_name="adopt-a2a",
        ),
        FeatureInfo(
            name="observability",
            description="Audit dashboard, traces, and spend tracking",
            module="keprix.providers.observability",
            version="0.5.0",
            requires_config=False,
            prompt_name="adopt-observability",
        ),
    ],
    "0.6.0": [
        FeatureInfo(
            name="notion",
            description="Notion workspace integration",
            module="keprix.integrations.notion",
            version="0.6.0",
            requires_config=True,
        ),
        FeatureInfo(
            name="semantic_cache",
            description="Semantic prompt cache for repeated LLM calls",
            module="keprix.providers.ops.prompt_cache",
            version="0.6.0",
            requires_config=False,
            prompt_name="adopt-cache",
        ),
    ],
    "0.7.0": [
        FeatureInfo(
            name="cli_auto_config",
            description="Auto-detect and configure external CLI tools",
            module="keprix.keprix_cli.self_config",
            version="0.7.0",
            requires_config=False,
        ),
    ],
}


class FeatureDiscovery:
    """Discovers features, breaking changes, and opt-in config between versions."""

    def __init__(self, registry: dict[str, list[FeatureInfo]] | None = None):
        self._registry = registry if registry is not None else FEATURE_REGISTRY

    def get_new_features(self, from_version: str, to_version: str) -> list[FeatureInfo]:
        features: list[FeatureInfo] = []
        for version in sorted(self._registry, key=version_tuple):
            if not version_gt(version, from_version):
                continue
            if not version_lte(version, to_version):
                continue
            features.extend(self._registry[version])
        return features

    def get_breaking_changes(self, from_version: str, to_version: str) -> list[FeatureInfo]:
        return [f for f in self.get_new_features(from_version, to_version) if f.breaking]

    def get_opt_in_features(self, from_version: str, to_version: str) -> list[FeatureInfo]:
        return [f for f in self.get_new_features(from_version, to_version) if f.requires_config]

    def feature_versions(self) -> list[str]:
        return sorted(self._registry.keys(), key=version_tuple)

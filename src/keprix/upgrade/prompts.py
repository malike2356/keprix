"""Guided feature adoption prompts for post-upgrade opt-in."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AdoptionPrompt:
    name: str
    title: str
    description: str
    feature_key: str
    feature_defaults: dict[str, Any]
    version: str = ""
    config_path: str | None = None
    config_defaults: dict[str, Any] | None = None
    risks: list[str] | None = None


ADOPTION_PROMPTS: dict[str, AdoptionPrompt] = {
    "adopt-a2a": AdoptionPrompt(
        name="adopt-a2a",
        title="A2A Protocol (Agent-to-Agent)",
        description="Enable agent-to-agent delegation and federated task execution.",
        feature_key="a2a",
        feature_defaults={"enabled": True},
        version="0.5.0",
        config_path="config/a2a.yaml",
        config_defaults={"agents": [], "trust_policy": "local_only"},
        risks=[
            "Network exposure for agent communication",
            "Additional latency per delegation",
        ],
    ),
    "adopt-billing": AdoptionPrompt(
        name="adopt-billing",
        title="Billing (Stripe subscriptions)",
        description="Enable Stripe subscriptions, plans, and webhooks.",
        feature_key="billing",
        feature_defaults={"enabled": True},
        version="0.4.0",
        config_path="billing.yaml",
        config_defaults={"provider": "stripe", "plans": []},
    ),
    "adopt-routing": AdoptionPrompt(
        name="adopt-routing",
        title="Combo routing",
        description="Enable combo routing with provider fallback.",
        feature_key="routing",
        feature_defaults={"enabled": True, "combos": True, "circuit_breaker": True},
        version="0.5.0",
    ),
    "adopt-compression": AdoptionPrompt(
        name="adopt-compression",
        title="Token compression",
        description="Enable RTK + Caveman token compression (opt-in).",
        feature_key="compression",
        feature_defaults={"enabled": True},
        version="0.5.0",
    ),
    "adopt-guardrails": AdoptionPrompt(
        name="adopt-guardrails",
        title="Guardrails",
        description="Enable PII masking and prompt injection defence.",
        feature_key="guardrails",
        feature_defaults={"enabled": True},
        version="0.5.0",
    ),
    "adopt-observability": AdoptionPrompt(
        name="adopt-observability",
        title="Observability",
        description="Enable audit dashboard, traces, and metrics.",
        feature_key="observability",
        feature_defaults={"enabled": True},
        version="0.5.0",
        config_path="config/observability.yaml",
        config_defaults={"audit": True, "traces": True},
    ),
    "adopt-cache": AdoptionPrompt(
        name="adopt-cache",
        title="Semantic prompt cache",
        description="Cache repeated LLM prompts to reduce cost.",
        feature_key="cache",
        feature_defaults={"enabled": True, "semantic": True},
        version="0.6.0",
    ),
}


def list_adoption_prompt_details() -> list[AdoptionPrompt]:
    return [ADOPTION_PROMPTS[name] for name in sorted(ADOPTION_PROMPTS)]


def list_adoption_prompts() -> list[str]:
    return sorted(ADOPTION_PROMPTS)


def apply_adoption_prompt(
    prompt_name: str,
    product_path: Path,
    *,
    assume_yes: bool = False,
) -> dict[str, Any]:
    """Apply a guided feature adoption prompt to a product directory."""
    prompt = ADOPTION_PROMPTS.get(prompt_name)
    if prompt is None:
        available = ", ".join(list_adoption_prompts())
        raise ValueError(f"Unknown prompt {prompt_name!r}. Available: {available}")

    root = product_path.expanduser().resolve()
    manifest_path = root / "keprix.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    if not assume_yes:
        print(f"\nFeature Adoption: {prompt.title}")
        print(f"  {prompt.description}")
        if prompt.risks:
            print("  Risks:")
            for risk in prompt.risks:
                print(f"    - {risk}")
        try:
            answer = input("\nApply this feature? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return {"applied": False, "reason": "cancelled"}
        if answer not in {"y", "yes"}:
            return {"applied": False, "reason": "declined"}

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    features = data.setdefault("features", {})
    if not isinstance(features, dict):
        features = {}
        data["features"] = features
    current = features.get(prompt.feature_key)
    if not isinstance(current, dict):
        current = {}
    current.update(prompt.feature_defaults)
    features[prompt.feature_key] = current
    manifest_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    config_written = None
    if prompt.config_path and prompt.config_defaults is not None:
        config_file = root / prompt.config_path
        if not config_file.exists():
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                yaml.dump(prompt.config_defaults, default_flow_style=False),
                encoding="utf-8",
            )
            config_written = str(config_file)

    return {
        "applied": True,
        "prompt": prompt.name,
        "feature": prompt.feature_key,
        "manifest": str(manifest_path),
        "config_written": config_written,
    }

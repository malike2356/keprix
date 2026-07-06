"""Legal policy definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LegalPolicy:
    policy_type: str
    version: str
    title: str
    summary: str
    full_text_url: str
    requires_re_acceptance: bool = True
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_type": self.policy_type,
            "version": self.version,
            "title": self.title,
            "summary": self.summary,
            "full_text_url": self.full_text_url,
            "requires_re_acceptance": self.requires_re_acceptance,
            "active": self.active,
        }


def _config_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "legal_policies.yaml"


def load_policies() -> list[LegalPolicy]:
    path = _config_path()
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    policies: list[LegalPolicy] = []
    for policy_type, row in (raw.get("policies") or {}).items():
        if not row.get("active", True):
            continue
        policies.append(
            LegalPolicy(
                policy_type=policy_type,
                version=str(row["version"]),
                title=str(row["title"]),
                summary=str(row.get("summary", "")),
                full_text_url=str(row.get("full_text_url", f"/legal/{policy_type}")),
                requires_re_acceptance=bool(row.get("requires_re_acceptance", True)),
                active=True,
            )
        )
    return policies


def get_active_policies() -> list[LegalPolicy]:
    return load_policies()


def get_policy_text(policy_type: str) -> str:
    path = Path(__file__).resolve().parents[3] / "config" / "legal_text" / f"{policy_type}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Policy text for {policy_type} is not configured."

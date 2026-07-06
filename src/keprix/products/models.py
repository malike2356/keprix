"""Data models for products built on Keprix (config-driven)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProductDefinition:
    """A product or vertical that extends Keprix via config, not core hardcoding."""

    id: str
    display_name: str
    audit_domain_pack: str | None = None
    extension_name: str | None = None
    domain_packs: list[str] = field(default_factory=list)
    domain_intent_files: list[str] = field(default_factory=list)
    glossary_files: list[str] = field(default_factory=list)
    playbook_localization_files: list[str] = field(default_factory=list)
    voice_category_files: list[str] = field(default_factory=list)
    regulated_domains: list[str] = field(default_factory=list)
    feature_flags: dict[str, bool] = field(default_factory=dict)
    env_flag: str | None = None

    @classmethod
    def from_dict(cls, product_id: str, row: dict[str, Any]) -> ProductDefinition:
        return cls(
            id=product_id,
            display_name=str(row.get("display_name") or product_id),
            audit_domain_pack=row.get("audit_domain_pack"),
            extension_name=row.get("extension_name"),
            domain_packs=[str(item) for item in row.get("domain_packs") or []],
            domain_intent_files=[str(item) for item in row.get("domain_intents") or []],
            glossary_files=[str(item) for item in row.get("glossaries") or []],
            playbook_localization_files=[
                str(item) for item in row.get("playbook_localization") or []
            ],
            voice_category_files=[str(item) for item in row.get("voice_categories") or []],
            regulated_domains=[str(item) for item in row.get("regulated_domains") or []],
            feature_flags={
                str(key): bool(value) for key, value in (row.get("feature_flags") or {}).items()
            },
            env_flag=str(row["env_flag"]) if row.get("env_flag") else None,
        )

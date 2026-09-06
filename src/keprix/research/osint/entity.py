"""Normalized OSINT investigation entities and identifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


IDENTIFIER_FIELDS = ("domain", "registration_id", "company_number", "cik", "qid", "identifier")


def normalize_identifier(kind: str, value: object) -> str:
    """Return a typed identifier key so values from different namespaces do not collide."""
    raw = str(value or "").strip().lower()
    raw = re.sub(r"^https?://", "", raw).rstrip("/")
    raw = re.sub(r"^www\.", "", raw)
    return f"{kind}:{raw}" if raw else ""


@dataclass
class Entity:
    kind: str
    name: str
    identifiers: set[str] = field(default_factory=set)
    seed: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in {"person", "company", "domain"}:
            raise ValueError("entity kind must be person, company, or domain")
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("entity name is required")
        self.identifiers.update(self._normalized_seed_identifiers())

    def _normalized_seed_identifiers(self) -> set[str]:
        values: set[str] = set()
        for kind, value in self.seed.items():
            normalized = normalize_identifier(kind, value)
            if normalized:
                values.add(normalized)
        return values

    def with_discovered(self, identifiers: dict[str, object]) -> "Entity":
        """Create the next-round entity without mutating the caller's seed."""
        seed = {**self.seed, **{key: str(value) for key, value in identifiers.items() if value}}
        return Entity(self.kind, self.name, identifiers=set(self.identifiers), seed=seed)

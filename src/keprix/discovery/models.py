"""Normalized discovery models (candidates, manifests, job status)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class AdapterHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"
    CIRCUIT_OPEN = "circuit_open"
    ERROR = "error"


@dataclass
class FieldProvenance:
    """Provenance for a single field on a LeadCandidate."""

    field: str
    source: str
    external_id: str | None = None
    content_hash: str | None = None
    observed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldProvenance:
        return cls(
            field=str(data.get("field") or ""),
            source=str(data.get("source") or ""),
            external_id=data.get("external_id"),
            content_hash=data.get("content_hash"),
            observed_at=data.get("observed_at"),
        )


@dataclass
class LeadCandidate:
    """Normalized lead candidate. Discovery never implies contactability."""

    company: str | None = None
    contacts: list[dict[str, Any]] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    geo: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    external_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    score_hint: float | None = None
    company_number: str | None = None
    domain: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    provenance: list[FieldProvenance] = field(default_factory=list)
    content_hash: str | None = None
    domain_pack: str = "generic"
    notes: str | None = None

    def ensure_hashes(self) -> None:
        if not self.content_hash:
            self.content_hash = content_hash_for(
                {
                    "company": self.company,
                    "company_number": self.company_number,
                    "external_id": self.external_id,
                    "urls": self.urls,
                    "emails": self.emails,
                    "phones": self.phones,
                    "source": self.source,
                }
            )
        for prov in self.provenance:
            if not prov.content_hash and prov.field:
                value = getattr(self, prov.field, None) if hasattr(self, prov.field) else None
                if value is None and isinstance(self.raw, dict):
                    value = self.raw.get(prov.field)
                prov.content_hash = content_hash_for({prov.field: value})

    def to_dict(self) -> dict[str, Any]:
        self.ensure_hashes()
        return {
            "company": self.company,
            "contacts": list(self.contacts),
            "urls": list(self.urls),
            "geo": dict(self.geo),
            "source": self.source,
            "external_id": self.external_id,
            "raw": dict(self.raw),
            "score_hint": self.score_hint,
            "company_number": self.company_number,
            "domain": self.domain,
            "emails": list(self.emails),
            "phones": list(self.phones),
            "provenance": [p.to_dict() for p in self.provenance],
            "content_hash": self.content_hash,
            "domain_pack": self.domain_pack,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LeadCandidate:
        provenance = [
            FieldProvenance.from_dict(p)
            for p in (data.get("provenance") or [])
            if isinstance(p, dict)
        ]
        cand = cls(
            company=data.get("company"),
            contacts=list(data.get("contacts") or []),
            urls=list(data.get("urls") or []),
            geo=dict(data.get("geo") or {}),
            source=str(data.get("source") or ""),
            external_id=data.get("external_id"),
            raw=dict(data.get("raw") or {}),
            score_hint=data.get("score_hint"),
            company_number=data.get("company_number"),
            domain=data.get("domain"),
            emails=list(data.get("emails") or []),
            phones=list(data.get("phones") or []),
            provenance=provenance,
            content_hash=data.get("content_hash"),
            domain_pack=str(data.get("domain_pack") or "generic"),
            notes=data.get("notes"),
        )
        cand.ensure_hashes()
        return cand


@dataclass
class AdapterManifest:
    """Licence / purpose / retention declaration for an adapter."""

    name: str
    title: str
    description: str = ""
    licence_ref: str = ""
    permitted_purpose: str = "lead_discovery_review"
    allowed_fields: list[str] = field(
        default_factory=lambda: [
            "company",
            "company_number",
            "urls",
            "geo",
            "contacts",
            "emails",
            "phones",
        ]
    )
    retention: str = "workspace_policy"
    jurisdiction: str = "UK"
    contact_use_eligible: bool = False
    outreach_allowed: bool = False
    source_licence: str = ""
    rate_limit_per_minute: int = 30
    domain_packs: list[str] = field(default_factory=lambda: ["generic"])
    requires_env: list[str] = field(default_factory=list)
    feature_flag: str | None = None
    experimental: bool = False
    docs_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterHealth:
    name: str
    status: AdapterHealthStatus
    message: str = ""
    configured: bool = False
    enabled: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": str(self.status),
            "message": self.message,
            "configured": self.configured,
            "enabled": self.enabled,
            "details": dict(self.details),
        }


@dataclass
class DiscoverLimits:
    max_results: int = 50
    max_pages: int = 3
    max_fetches: int = 0
    budget_units: float = 100.0
    allow_homepage_fetch: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> DiscoverLimits:
        data = data or {}
        return cls(
            max_results=int(data.get("max_results") or 50),
            max_pages=int(data.get("max_pages") or 3),
            max_fetches=int(data.get("max_fetches") or 0),
            budget_units=float(data.get("budget_units") or 100.0),
            allow_homepage_fetch=bool(data.get("allow_homepage_fetch") or False),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiscoverQuery:
    text: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    domain_pack: str = "generic"
    workspace_id: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "params": dict(self.params),
            "domain_pack": self.domain_pack,
            "workspace_id": self.workspace_id,
        }


def content_hash_for(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


HIGH_RISK_DOMAIN_PACKS = frozenset(
    {
        "health",
        "health_social",
        "healthcare",
        "social_care",
        "care",
    }
)

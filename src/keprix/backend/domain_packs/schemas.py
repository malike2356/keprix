"""Domain knowledge pack schemas (Prompt 30)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

HIGH_STAKES_DOMAINS = frozenset(
    {
        "healthcare",
        "legal",
        "finance",
        "insurance",
        "employment",
        "safety",
        "construction",
        "cybersecurity",
    }
)

REGULATED_JURISDICTION_TAGS = frozenset({"EU", "UK", "US", "GH", "NG", "ZA", "KE"})


@dataclass
class PackSource:
    title: str
    url: str
    citation: str
    source_type: str = "web"
    jurisdiction: str | None = None
    retrieved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "citation": self.citation,
            "source_type": self.source_type,
            "jurisdiction": self.jurisdiction,
            "retrieved_at": self.retrieved_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackSource:
        return cls(
            title=str(data.get("title") or ""),
            url=str(data.get("url") or ""),
            citation=str(data.get("citation") or ""),
            source_type=str(data.get("source_type") or "web"),
            jurisdiction=data.get("jurisdiction"),
            retrieved_at=data.get("retrieved_at"),
        )


@dataclass
class GlossaryTerm:
    term: str
    definition: str
    locale: str = "en"
    approved_equivalent: str | None = None
    forbidden_translations: list[str] = field(default_factory=list)
    voice_friendly: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "definition": self.definition,
            "locale": self.locale,
            "approved_equivalent": self.approved_equivalent,
            "forbidden_translations": list(self.forbidden_translations),
            "voice_friendly": self.voice_friendly,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlossaryTerm:
        return cls(
            term=str(data.get("term") or ""),
            definition=str(data.get("definition") or ""),
            locale=str(data.get("locale") or "en"),
            approved_equivalent=data.get("approved_equivalent"),
            forbidden_translations=list(data.get("forbidden_translations") or []),
            voice_friendly=data.get("voice_friendly"),
        )


@dataclass
class DomainPackManifest:
    id: str
    domain_name: str
    version: str
    jurisdictions: list[str] = field(default_factory=list)
    sources: list[PackSource] = field(default_factory=list)
    source_quality_score: float = 0.0
    updated_at: str = ""
    glossary: list[GlossaryTerm] = field(default_factory=list)
    common_tasks: list[str] = field(default_factory=list)
    playbooks: list[dict[str, str]] = field(default_factory=list)
    disclaimers: list[str] = field(default_factory=list)
    data_schemas: list[dict[str, Any]] = field(default_factory=list)
    tool_permissions: list[str] = field(default_factory=list)
    localization_coverage: dict[str, Any] = field(default_factory=dict)
    tests: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    can_do: list[str] = field(default_factory=list)
    cannot_do: list[str] = field(default_factory=list)
    review_status: str = "draft"
    review_required: bool = False
    hub_published: bool = False
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "domain_name": self.domain_name,
            "version": self.version,
            "jurisdictions": list(self.jurisdictions),
            "sources": [row.to_dict() for row in self.sources],
            "source_quality_score": self.source_quality_score,
            "updated_at": self.updated_at,
            "glossary": [row.to_dict() for row in self.glossary],
            "common_tasks": list(self.common_tasks),
            "playbooks": list(self.playbooks),
            "disclaimers": list(self.disclaimers),
            "data_schemas": list(self.data_schemas),
            "tool_permissions": list(self.tool_permissions),
            "localization_coverage": dict(self.localization_coverage),
            "tests": list(self.tests),
            "limitations": list(self.limitations),
            "can_do": list(self.can_do),
            "cannot_do": list(self.cannot_do),
            "review_status": self.review_status,
            "review_required": self.review_required,
            "hub_published": self.hub_published,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainPackManifest:
        return cls(
            id=str(data["id"]),
            domain_name=str(data.get("domain_name") or data.get("domain") or ""),
            version=str(data.get("version") or "0.1.0"),
            jurisdictions=list(data.get("jurisdictions") or []),
            sources=[PackSource.from_dict(row) for row in (data.get("sources") or [])],
            source_quality_score=float(data.get("source_quality_score") or 0.0),
            updated_at=str(data.get("updated_at") or ""),
            glossary=[GlossaryTerm.from_dict(row) for row in (data.get("glossary") or [])],
            common_tasks=list(data.get("common_tasks") or []),
            playbooks=[dict(row) for row in (data.get("playbooks") or [])],
            disclaimers=list(data.get("disclaimers") or []),
            data_schemas=list(data.get("data_schemas") or []),
            tool_permissions=list(data.get("tool_permissions") or []),
            localization_coverage=dict(data.get("localization_coverage") or {}),
            tests=list(data.get("tests") or []),
            limitations=list(data.get("limitations") or []),
            can_do=list(data.get("can_do") or []),
            cannot_do=list(data.get("cannot_do") or []),
            review_status=str(data.get("review_status") or "draft"),
            review_required=bool(data.get("review_required")),
            hub_published=bool(data.get("hub_published")),
            status=str(data.get("status") or "draft"),
        )

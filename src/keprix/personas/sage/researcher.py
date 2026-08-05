"""Research pipeline and source management for SAGE."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC, StrEnum
from typing import Any
from uuid import uuid4

from keprix.memory.rag.indexer import RagIndexer
from keprix.personas.sage.persona import SAGE_PERSONA
from keprix.research.search import web_search


class Confidence(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class StatementType(StrEnum):
    FACT = "fact"
    ANALYSIS = "analysis"
    OPINION = "opinion"


MIN_SOURCES = 3

TRUSTED_DOMAIN_MARKERS = (".gov", ".edu", ".ac.uk", "who.int", "nature.com", "arxiv.org")
OPINION_MARKERS = ("i believe", "in my view", "we think", "likely", "probably", "may", "might")
FACT_MARKERS = ("according to", "data shows", "study found", "reported", "research indicates", "evidence suggests")


@dataclass(slots=True)
class SourceCredibility:
    title: str
    url: str
    authority: int
    recency: int
    bias: int
    corroboration: int
    total: int
    rating: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "authority": self.authority,
            "recency": self.recency,
            "bias": self.bias,
            "corroboration": self.corroboration,
            "total": self.total,
            "rating": self.rating,
        }


@dataclass(slots=True)
class ClaimVerification:
    claim: str
    statement_type: str
    verified: bool
    confidence: str
    supporting_sources: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "statement_type": self.statement_type,
            "verified": self.verified,
            "confidence": self.confidence,
            "supporting_sources": list(self.supporting_sources),
            "note": self.note,
        }


@dataclass
class ResearchResult:
    research_id: str
    query: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    credibility_scores: list[SourceCredibility] = field(default_factory=list)
    synthesis: str = ""
    claims: list[ClaimVerification] = field(default_factory=list)
    meets_source_minimum: bool = False
    indexed_chunks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_id": self.research_id,
            "query": self.query,
            "sources": self.sources,
            "credibility_scores": [score.to_dict() for score in self.credibility_scores],
            "synthesis": self.synthesis,
            "claims": [claim.to_dict() for claim in self.claims],
            "meets_source_minimum": self.meets_source_minimum,
            "indexed_chunks": self.indexed_chunks,
        }


class SageResearcher:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = SAGE_PERSONA
        self._indexer = RagIndexer()

    def score_source(self, source: dict[str, Any], *, corroboration_count: int = 0) -> SourceCredibility:
        url = source.get("url", "").lower()
        snippet = (source.get("snippet") or source.get("excerpt") or "").lower()

        authority = 10
        if any(marker in url for marker in TRUSTED_DOMAIN_MARKERS):
            authority = 28
        elif any(marker in url for marker in ("reuters.com", "bbc.co", "nytimes.com", "docs.")):
            authority = 20
        elif "wikipedia.org" in url:
            authority = 15

        recency = 18 if source.get("date") else 8
        if source.get("published"):
            recency = 16

        bias = 16
        if any(marker in snippet for marker in OPINION_MARKERS):
            bias = 6
        if any(marker in snippet for marker in ("sponsored", "advertisement", "buy now")):
            bias = 4

        corroboration = min(30, corroboration_count * 10)
        total = min(100, authority + recency + bias + corroboration)
        if total >= 70:
            rating = Confidence.HIGH
        elif total >= 45:
            rating = Confidence.MEDIUM
        else:
            rating = Confidence.LOW

        return SourceCredibility(
            title=source.get("title", "Unknown"),
            url=source.get("url", ""),
            authority=authority,
            recency=recency,
            bias=bias,
            corroboration=corroboration,
            total=total,
            rating=rating,
        )

    def classify_statement(self, text: str) -> str:
        lowered = text.lower()
        if any(marker in lowered for marker in OPINION_MARKERS):
            return StatementType.OPINION
        if any(marker in lowered for marker in FACT_MARKERS):
            return StatementType.FACT
        if re.search(r"\b(should|recommend|suggest)\b", lowered):
            return StatementType.ANALYSIS
        return StatementType.ANALYSIS

    def verify_claim(self, claim: str, sources: list[dict[str, Any]]) -> ClaimVerification:
        statement_type = self.classify_statement(claim)
        claim_tokens = {token for token in re.findall(r"[a-z]{4,}", claim.lower()) if len(token) > 4}
        supporting: list[str] = []

        for source in sources:
            blob = f"{source.get('title', '')} {source.get('snippet', '')} {source.get('excerpt', '')}".lower()
            overlap = sum(1 for token in claim_tokens if token in blob)
            if overlap >= 2:
                supporting.append(source.get("url", source.get("title", "")))

        verified = len(supporting) >= MIN_SOURCES and statement_type != StatementType.OPINION
        if statement_type == StatementType.OPINION:
            confidence = Confidence.LOW
            note = "Opinion statements are not verified as fact"
        elif len(supporting) >= MIN_SOURCES:
            confidence = Confidence.HIGH
            note = f"Corroborated by {len(supporting)} sources"
        elif len(supporting) >= 1:
            confidence = Confidence.MEDIUM
            note = f"Partial corroboration ({len(supporting)} source(s)); need {MIN_SOURCES} for high confidence"
        else:
            confidence = Confidence.LOW
            note = "Unverified; no supporting sources found"

        return ClaimVerification(
            claim=claim,
            statement_type=statement_type,
            verified=verified,
            confidence=confidence,
            supporting_sources=supporting,
            note=note,
        )

    def _corroboration_counts(self, sources: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {source.get("url", ""): 0 for source in sources}
        for source in sources:
            url = source.get("url", "")
            blob = f"{source.get('title', '')} {source.get('snippet', '')}".lower()
            matches = 0
            for other in sources:
                if other.get("url") == url:
                    continue
                other_blob = f"{other.get('title', '')} {other.get('snippet', '')}".lower()
                shared = set(re.findall(r"[a-z]{5,}", blob)) & set(re.findall(r"[a-z]{5,}", other_blob))
                if len(shared) >= 3:
                    matches += 1
            counts[url] = matches
        return counts

    def synthesize(self, query: str, sources: list[dict[str, Any]], scores: list[SourceCredibility]) -> str:
        if not sources:
            return f"No sources found for: {query}"

        facts: list[str] = []
        opinions: list[str] = []
        for source, score in zip(sources, scores):
            snippet = source.get("snippet") or source.get("excerpt") or ""
            sentence = snippet.split(".")[0].strip() if snippet else source.get("title", "")
            if not sentence:
                continue
            kind = self.classify_statement(sentence)
            citation = f"[{source.get('title', 'Source')}, {source.get('date', 'n.d.')}, {source.get('url', '')}]"
            line = f"- {sentence} {citation} (credibility: {score.rating})"
            if kind == StatementType.OPINION:
                opinions.append(line)
            else:
                facts.append(line)

        parts = [f"## Research synthesis: {query}", "", "### Facts and evidence", ""]
        parts.extend(facts or ["- Insufficient corroborated facts; gather more sources."])
        parts.extend(["", "### Analysis and opinion", ""])
        parts.extend(opinions or ["- No explicit opinion markers detected in source snippets."])
        return "\n".join(parts)

    async def research(
        self,
        query: str,
        *,
        sources: list[dict[str, Any]] | None = None,
        claims: list[str] | None = None,
        search_backend: str = "searxng",
        limit: int = 5,
        index_to_rag: bool = True,
    ) -> ResearchResult:
        research_id = str(uuid4())
        gathered = list(sources or [])
        if not gathered:
            gathered = await web_search(query, backend=search_backend, limit=max(limit, MIN_SOURCES))

        corroboration = self._corroboration_counts(gathered)
        scores = [
            self.score_source(source, corroboration_count=corroboration.get(source.get("url", ""), 0))
            for source in gathered
        ]
        synthesis = self.synthesize(query, gathered, scores)
        verifications = [self.verify_claim(claim, gathered) for claim in (claims or [])]

        result = ResearchResult(
            research_id=research_id,
            query=query,
            sources=gathered,
            credibility_scores=scores,
            synthesis=synthesis,
            claims=verifications,
            meets_source_minimum=len(gathered) >= MIN_SOURCES,
        )

        if index_to_rag:
            metadata = (
                f"<!-- sage-research id={research_id} query={query} "
                f"sources={len(gathered)} indexed_at={datetime.now(UTC).isoformat()} -->\n"
            )
            result.indexed_chunks = await self.index_findings(
                research_id,
                metadata + synthesis,
            )

        return result

    async def index_findings(self, research_id: str, content: str) -> int:
        return await self._indexer.ingest(
            user_id=self.user_id,
            source_type="sage_research",
            source_id=research_id,
            content=content,
        )

    def format_citation(self, source: dict[str, Any]) -> str:
        return f"[{source.get('title', 'Source')}, {source.get('date', 'n.d.')}, {source.get('url', '')}]"

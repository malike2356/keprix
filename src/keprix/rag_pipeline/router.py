"""RAG pipeline routing by query type, language, source, confidence, cost, and safety."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from keprix.rag_pipeline.component import PipelineComponent, PipelineContext


@dataclass
class RouteDecision:
    route: str
    reason: str
    policy_hits: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "reason": self.reason,
            "policy_hits": self.policy_hits,
        }


class PipelineRouter(PipelineComponent):
    name = "router"

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.35,
        cost_limit: float = 1.0,
        blocked_terms: list[str] | None = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.cost_limit = cost_limit
        self.blocked_terms = [term.lower() for term in (blocked_terms or ["password", "ssn", "credit card"])]

    def decide(self, ctx: PipelineContext) -> RouteDecision:
        policy_hits: list[str] = []
        query = ctx.query.lower()

        if any(term in query for term in self.blocked_terms):
            policy_hits.append("safety_policy")
            return RouteDecision(route="blocked", reason="Query matched safety policy", policy_hits=policy_hits)

        if ctx.cost_units >= self.cost_limit:
            policy_hits.append("cost_limit")
            return RouteDecision(route="clarification", reason="Cost limit reached", policy_hits=policy_hits)

        if self._is_research_query(query):
            policy_hits.append("query_type:research")
            if ctx.confidence < self.confidence_threshold:
                return RouteDecision(
                    route="deep_research",
                    reason="Research query with low retrieval confidence",
                    policy_hits=policy_hits,
                )

        if self._detect_language(query) != "en" and ctx.confidence < self.confidence_threshold:
            policy_hits.append("language:non_en")
            return RouteDecision(route="clarification", reason="Low confidence for non-English query", policy_hits=policy_hits)

        source_types = ctx.metadata.get("source_types") or []
        if source_types and not ctx.retrieved:
            policy_hits.append("document_source:miss")
            return RouteDecision(route="deep_research", reason="Requested source not retrieved", policy_hits=policy_hits)

        if ctx.confidence < self.confidence_threshold:
            policy_hits.append("confidence:low")
            return RouteDecision(route="clarification", reason="Low retrieval confidence", policy_hits=policy_hits)

        return RouteDecision(route="direct_answer", reason="Confidence acceptable", policy_hits=policy_hits)

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        decision = self.decide(ctx)
        ctx.route = decision.route
        ctx.metadata["route_decision"] = decision.to_dict()
        ctx.trace.append({"component": self.name, **decision.to_dict()})
        return ctx

    def _is_research_query(self, query: str) -> bool:
        return bool(re.search(r"\b(compare|analyze|research|survey|deep dive|literature)\b", query))

    def _detect_language(self, query: str) -> str:
        if re.search(r"[\u0400-\u04FF]", query):
            return "ru"
        if re.search(r"[\u4E00-\u9FFF]", query):
            return "zh"
        if re.search(r"[\u0600-\u06FF]", query):
            return "ar"
        return "en"

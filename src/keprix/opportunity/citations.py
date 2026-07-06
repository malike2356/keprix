"""Citation tracking for opportunity research artifacts."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from keprix.opportunity.models import OpportunityCitation, OpportunityPhase
from keprix.opportunity.workspace import read_opportunity_json, update_opportunity_json


def add_citation(
    *,
    workspace_id: str,
    opportunity_id: str,
    url: str,
    title: str = "",
    snippet: str = "",
    phase: OpportunityPhase | None = None,
    artifact_filename: str | None = None,
    source: str = "research",
) -> OpportunityCitation:
    citation_id = "cite-" + secrets.token_hex(4)
    now = datetime.now(timezone.utc)
    citation = OpportunityCitation(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        citation_id=citation_id,
        url=url,
        title=title,
        snippet=snippet,
        phase=phase,
        artifact_filename=artifact_filename,
        source=source,
        created_at=now,
        updated_at=now,
    )
    meta = read_opportunity_json(opportunity_id)
    citations: list[dict[str, Any]] = list(meta.get("citations", []))
    citations.append(citation.model_dump(mode="json"))
    update_opportunity_json(opportunity_id, {"citations": citations})
    return citation


def list_citations(opportunity_id: str) -> list[OpportunityCitation]:
    meta = read_opportunity_json(opportunity_id)
    out: list[OpportunityCitation] = []
    for row in meta.get("citations", []):
        out.append(OpportunityCitation(**row))
    return out


def format_citations_block(citations: list[OpportunityCitation]) -> str:
    if not citations:
        return ""
    lines = ["\n## Sources\n"]
    for index, cite in enumerate(citations, start=1):
        label = cite.title or cite.url
        lines.append(f"{index}. [{label}]({cite.url})")
        if cite.snippet:
            lines.append(f"   - {cite.snippet}")
    return "\n".join(lines) + "\n"

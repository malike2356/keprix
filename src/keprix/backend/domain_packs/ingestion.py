"""Source ingestion for domain packs (Prompt 30)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.backend.domain_packs.schemas import DomainPackManifest, PackSource
from keprix.backend.domain_packs.source_quality import compute_pack_quality_score


def ingest_sources(pack: DomainPackManifest, rows: list[dict[str, Any]]) -> DomainPackManifest:
    ingested: list[PackSource] = []
    for row in rows:
        ingested.append(
            PackSource(
                title=str(row.get("title") or "Untitled source"),
                url=str(row.get("url") or ""),
                citation=str(row.get("citation") or ""),
                source_type=str(row.get("source_type") or "web"),
                jurisdiction=row.get("jurisdiction"),
                retrieved_at=str(row.get("retrieved_at") or datetime.now(timezone.utc).isoformat()),
            )
        )
    pack.sources.extend(ingested)
    pack.source_quality_score = compute_pack_quality_score(pack)
    return pack

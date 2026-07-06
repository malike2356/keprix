"""Source quality scoring for domain packs (Prompt 30)."""

from __future__ import annotations

from urllib.parse import urlparse

from keprix.backend.domain_packs.schemas import DomainPackManifest, PackSource


def score_source(source: PackSource) -> float:
    score = 0.0
    if source.title.strip():
        score += 0.2
    if source.url.strip() and urlparse(source.url).scheme in {"http", "https", "file"}:
        score += 0.2
    if source.citation.strip():
        score += 0.4
    if source.jurisdiction:
        score += 0.1
    if source.retrieved_at:
        score += 0.1
    return min(score, 1.0)


def source_quality_errors(pack: DomainPackManifest) -> list[str]:
    errors: list[str] = []
    if not pack.sources:
        errors.append("at least one source is required")
        return errors
    for index, source in enumerate(pack.sources, start=1):
        if not source.citation.strip():
            errors.append(f"source {index} missing citation")
        if not source.url.strip():
            errors.append(f"source {index} missing url")
    return errors


def compute_pack_quality_score(pack: DomainPackManifest) -> float:
    if not pack.sources:
        return 0.0
    scores = [score_source(source) for source in pack.sources]
    return round(sum(scores) / len(scores), 3)

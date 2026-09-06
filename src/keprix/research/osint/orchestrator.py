"""Bounded multi-round OSINT correlation orchestration."""

from __future__ import annotations

import uuid
from typing import Any, Callable, Iterable

from .entity import Entity, IDENTIFIER_FIELDS, normalize_identifier
from .synthesis import synthesize

Source = Callable[[Entity], Iterable[dict[str, Any]]]


def _identifiers(hit: dict[str, Any]) -> set[str]:
    return {
        normalized
        for key in IDENTIFIER_FIELDS
        if (normalized := normalize_identifier(key, hit.get(key)))
    }


def _correlate(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[int]] = {}
    for index, hit in enumerate(hits):
        for identifier in _identifiers(hit):
            groups.setdefault(identifier, []).append(index)
    return [
        {
            "identifier": identifier,
            "hit_indexes": indexes,
            "source_count": len({hits[index].get("source") for index in indexes}),
            "confidence": min(1.0, 0.5 + 0.25 * (len({hits[index].get("source") for index in indexes}) - 1)),
        }
        for identifier, indexes in groups.items()
        if len({hits[index].get("source") for index in indexes}) > 1
    ]


def investigate(
    *,
    workspace_id: str,
    entity: Entity,
    sources: dict[str, Source],
    depth_cap: int = 2,
    enabled: bool = True,
    acknowledge_lawful_use: bool = False,
    run_store: Any | None = None,
) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled", "reason": "OSINT is disabled by workspace policy"}
    if not acknowledge_lawful_use:
        return {"status": "acknowledgement_required", "reason": "lawful-use acknowledgement is required"}
    if not sources:
        return {"status": "no_sources", "reason": "no OSINT source adapters are enabled"}
    if depth_cap < 1:
        return {"status": "invalid_depth_cap", "reason": "depth_cap must be at least 1"}
    hits: list[dict[str, Any]] = []
    seen: set[str] = set(entity.identifiers)
    seen_hits: set[str] = set()
    rounds = 0
    current_entity = entity
    for rounds in range(depth_cap):
        before = len(hits)
        for name, source in sources.items():
            for hit in source(current_entity):
                if not isinstance(hit, dict):
                    continue
                hit = {**hit, "source": name}
                hit_ids = _identifiers(hit)
                hit_key = "|".join([str(hit.get("source") or "")] + sorted(hit_ids or {str(hit.get("url") or hit.get("claim") or "")}))
                if hit_key in seen_hits:
                    continue
                seen_hits.add(hit_key)
                seen.update(hit_ids)
                hits.append(hit)
        discovered = {
            identifier.split(":", 1)[0]: identifier.split(":", 1)[1]
            for identifier in seen - current_entity.identifiers
            if ":" in identifier
        }
        if discovered:
            current_entity = current_entity.with_discovered(discovered)
        if len(hits) == before:
            break
    correlations = _correlate(hits)
    report = synthesize({"kind": entity.kind, "name": entity.name, "identifiers": sorted(seen)}, hits, correlations)
    run_id = f"osint-{uuid.uuid4().hex[:10]}"
    if run_store is not None:
        project = run_store.create_project(title=f"OSINT: {entity.name}", question=f"Investigate {entity.name}")
        run_store.save_object(object_id=run_id, object_type="investigation", project_id=project["project_id"], owner="agent", source_ref=None, provenance={"workspace_id": workspace_id, "rounds": rounds + 1}, payload=report, trace_id=run_id)
    return {"status": "complete", "run_id": run_id, "rounds": rounds + 1, "depth_cap": depth_cap, "report": report}

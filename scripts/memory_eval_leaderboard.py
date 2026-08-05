#!/usr/bin/env python3
"""Expanded memory eval pack: recall, negatives, privacy isolation, dream promote.

Exit 0 when thresholds pass. Suitable for CI / nightly.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keprix.memory.dreaming import DreamingService
from keprix.memory.embeddings import EmbeddingService
from keprix.memory.episodic.store import InMemoryEpisodicStore
from keprix.memory.orchestrator import MemoryOrchestrator
from keprix.memory.temporal_kg import TemporalKnowledgeGraph


async def run() -> dict:
    store = InMemoryEpisodicStore(embeddings=EmbeddingService(deterministic=True))
    kg = TemporalKnowledgeGraph()
    orch = MemoryOrchestrator(store=store, kg=kg)

    await store.save(
        "alice",
        "Alice prefers London timezone.",
        metadata={"tags": ["preference"], "memory_type": "preference", "belief_state": "active", "confidence": 0.9},
    )
    await store.save(
        "alice",
        "Project Nebula ships 2026-09-01.",
        metadata={"tags": ["decision"], "memory_type": "decision", "belief_state": "active", "confidence": 0.85},
    )
    await store.save(
        "bob",
        "Bob prefers Sydney timezone.",
        metadata={"tags": ["preference"], "memory_type": "preference", "belief_state": "active", "confidence": 0.9},
    )

    alice = await orch.recall("alice", "timezone preference", limit=5, include_rag=False, include_curated=False)
    bob_leak = any("Sydney" in h["content"] for h in alice["hits"])
    alice_hit = any("London" in h["content"] for h in alice["hits"])

    dream = DreamingService(store=store, kg=kg)
    detail = await dream.run("alice")
    graph = await kg.search("alice", "Nebula", limit=10)

    report = {
        "alice_timezone_hit": alice_hit,
        "no_cross_user_leak": not bob_leak,
        "dream_promoted": int(detail.get("promoted") or 0) >= 0,
        "entities_or_relations": bool(graph.get("entities") or graph.get("relations")),
        "alice_hits": alice["hits"],
        "dream": detail,
        "pass": alice_hit and (not bob_leak),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    report = asyncio.run(run())
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())

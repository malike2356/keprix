#!/usr/bin/env python3
"""Episodic memory recall benchmark (local smoke / CI starter).

Usage:
  python scripts/memory_recall_benchmark.py
  python scripts/memory_recall_benchmark.py --out /tmp/memory-bench.json

Writes facts, runs queries, reports recall@k. Uses in-memory store +
deterministic embeddings so it works offline without PG.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keprix.memory.embeddings import EmbeddingService
from keprix.memory.episodic.store import InMemoryEpisodicStore


@dataclass
class Case:
    query: str
    expect_contains: list[str]
    must_not_contain: list[str]


GOLD: list[tuple[str, list[str], Case]] = [
    (
        "User prefers London timezone and morning standups.",
        ["preference", "work"],
        Case(
            query="What timezone does the user prefer?",
            expect_contains=["London"],
            must_not_contain=["Sydney"],
        ),
    ),
    (
        "Project Codename Nebula ships on 2026-09-01.",
        ["project", "deadline"],
        Case(
            query="When does Nebula ship?",
            expect_contains=["2026-09-01", "Nebula"],
            must_not_contain=["Codename Orion"],
        ),
    ),
    (
        "Do not mention the surprise birthday party for Sam.",
        ["privacy"],
        Case(
            query="party plans",
            expect_contains=["Sam", "birthday"],
            must_not_contain=[],
        ),
    ),
]


async def run(k: int = 5) -> dict:
    store = InMemoryEpisodicStore(embeddings=EmbeddingService(deterministic=True))
    user_id = "bench-user"
    for content, tags, _case in GOLD:
        await store.save(user_id, content, metadata={"tags": tags})

    hits = 0
    negatives_ok = 0
    details = []
    for _content, _tags, case in GOLD:
        results = await store.search(user_id, case.query, limit=k)
        blob = "\n".join(item.content for item in results)
        hit = all(token.lower() in blob.lower() for token in case.expect_contains)
        clean = all(token.lower() not in blob.lower() for token in case.must_not_contain)
        hits += int(hit)
        negatives_ok += int(clean)
        details.append(
            {
                "query": case.query,
                "hit": hit,
                "negatives_ok": clean,
                "top": [{"id": r.id, "score": r.score, "content": r.content} for r in results],
            }
        )

    total = len(GOLD)
    report = {
        "recall_at_k": hits / total if total else 0.0,
        "negative_filter_rate": negatives_ok / total if total else 0.0,
        "k": k,
        "cases": total,
        "details": details,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--min-recall", type=float, default=0.66)
    args = parser.parse_args()
    report = asyncio.run(run(k=args.k))
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    ok = report["recall_at_k"] >= args.min_recall
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

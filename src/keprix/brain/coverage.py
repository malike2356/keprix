"""Coverage gap detection for brain health."""

from __future__ import annotations

import re
from collections import Counter

from keprix.brain.graph_types import GraphNode

STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "for",
    "to",
    "of",
    "in",
    "on",
    "with",
    "from",
    "by",
    "is",
    "was",
    "are",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "be",
    "as",
    "at",
    "into",
    "about",
    "over",
    "under",
    "between",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "up",
    "down",
    "out",
    "off",
    "then",
    "than",
    "when",
    "where",
    "while",
    "who",
    "whom",
    "which",
    "what",
    "how",
    "why",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "too",
    "very",
    "can",
    "will",
    "just",
    "don",
    "should",
    "now",
    "memory",
    "note",
    "item",
    "topic",
    "alpha",
    "node",
}

PHRASE_RE = re.compile(r"[a-z][a-z0-9]+(?:\s+[a-z][a-z0-9]+){0,2}")


def _phrases_for_node(node: GraphNode) -> list[str]:
    text = f"{node.label} {node.summary}".lower()
    found = PHRASE_RE.findall(text)
    phrases: list[str] = []
    for phrase in found:
        tokens = phrase.split()
        if any(token in STOP_WORDS for token in tokens):
            continue
        if len(phrase) < 4:
            continue
        phrases.append(phrase)
    if not phrases:
        tokens = [token for token in re.findall(r"[a-z]{4,}", text) if token not in STOP_WORDS]
        phrases.extend(tokens[:2])
    return phrases


def detect_coverage_gaps(memories: list[GraphNode], *, min_memories: int = 3) -> list[str]:
    counts: Counter[str] = Counter()
    for node in memories:
        if node.kind != "memory":
            continue
        for phrase in _phrases_for_node(node):
            counts[phrase] += 1

    gaps = [phrase for phrase, count in counts.items() if count < min_memories]
    gaps.sort(key=lambda phrase: (counts[phrase], phrase))
    return gaps[:20]

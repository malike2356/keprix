"""Duplicate memory detection for brain health."""

from __future__ import annotations

import os
import re
from collections import defaultdict

from keprix.brain.graph_types import GraphNode
from keprix.memory.embeddings import EmbeddingService, cosine_similarity

SHINGLE_SIZE = 5
EMBEDDING_THRESHOLD = 0.85
FUZZY_THRESHOLD = 0.60


def word_jaccard_similarity(left: str, right: str) -> float:
    left_words = set(re.findall(r"[a-z0-9]+", left.lower()))
    right_words = set(re.findall(r"[a-z0-9]+", right.lower()))
    if not left_words or not right_words:
        return 0.0
    intersection = len(left_words & right_words)
    union = len(left_words | right_words)
    return intersection / union if union else 0.0


def fuzzy_similarity(left: str, right: str) -> float:
    return max(jaccard_similarity(left, right), word_jaccard_similarity(left, right))


def _shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    normalized = " ".join(text.lower().split())
    if len(normalized) <= size:
        return {normalized} if normalized else set()
    return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}


def jaccard_similarity(left: str, right: str) -> float:
    left_set = _shingles(left)
    right_set = _shingles(right)
    if not left_set or not right_set:
        return 0.0
    intersection = len(left_set & right_set)
    union = len(left_set | right_set)
    return intersection / union if union else 0.0


def find_duplicate_candidates_fuzzy(memories: list[GraphNode]) -> list[list[str]]:
    groups: list[list[str]] = []
    visited: set[str] = set()
    memory_nodes = [node for node in memories if node.kind == "memory"]
    for index, left in enumerate(memory_nodes):
        if left.id in visited:
            continue
        group = [left.id]
        left_text = f"{left.label} {left.summary}"
        for right in memory_nodes[index + 1 :]:
            if right.id in visited:
                continue
            right_text = f"{right.label} {right.summary}"
            if fuzzy_similarity(left_text, right_text) >= FUZZY_THRESHOLD:
                group.append(right.id)
                visited.add(right.id)
        if len(group) > 1:
            visited.update(group)
            groups.append(group)
    return groups


async def find_duplicate_candidates_embedding(memories: list[GraphNode]) -> list[list[str]]:
    memory_nodes = [node for node in memories if node.kind == "memory"]
    if len(memory_nodes) < 2:
        return []

    embeddings = EmbeddingService(
        deterministic=os.getenv("KEPRIX_EMBEDDING_DETERMINISTIC", "").lower() in {"1", "true", "yes"}
        or not os.getenv("KEPRIX_ML_SERVICE_URL")
    )
    vectors = await embeddings.embed_many([f"{node.label} {node.summary}" for node in memory_nodes])
    parent = list(range(len(memory_nodes)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: int, right: int) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for left in range(len(memory_nodes)):
        for right in range(left + 1, len(memory_nodes)):
            if cosine_similarity(vectors[left], vectors[right]) >= EMBEDDING_THRESHOLD:
                union(left, right)

    grouped: dict[int, list[str]] = defaultdict(list)
    for index, node in enumerate(memory_nodes):
        grouped[find(index)].append(node.id)
    return [group for group in grouped.values() if len(group) > 1]


async def find_duplicate_candidates(memories: list[GraphNode]) -> list[list[str]]:
    if len(memories) < 2:
        return []
    try:
        groups = await find_duplicate_candidates_embedding(memories)
        if groups:
            return groups
    except Exception:
        pass
    return find_duplicate_candidates_fuzzy(memories)

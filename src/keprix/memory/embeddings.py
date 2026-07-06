"""Embedding service with Gemini primary and OpenAI fallback."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Protocol

import httpx
import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...


def _deterministic_embedding(text: str, dims: int = EMBEDDING_DIM) -> list[float]:
    vector = np.zeros(dims, dtype=np.float32)
    for token in re.findall(r"\w+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        idx = int(digest, 16) % dims
        vector[idx] += 1.0
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector.tolist()
    return (vector / norm).tolist()


class EmbeddingService:
    def __init__(
        self,
        *,
        gemini_api_key: str | None = None,
        openai_api_key: str | None = None,
        deterministic: bool | None = None,
    ) -> None:
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        env_det = os.getenv("KEPRIX_EMBEDDING_DETERMINISTIC", "").lower() in {"1", "true", "yes"}
        self.deterministic = deterministic if deterministic is not None else env_det

    async def embed(self, text: str) -> list[float]:
        if self.deterministic or (not self.gemini_api_key and not self.openai_api_key):
            return _deterministic_embedding(text)
        try:
            return await self._embed_gemini(text)
        except Exception as exc:
            logger.warning("Gemini embedding failed, falling back: %s", exc)
            if self.openai_api_key:
                return await self._embed_openai(text)
            return _deterministic_embedding(text)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]

    async def _embed_gemini(self, text: str) -> list[float]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "text-embedding-004:embedContent"
        )
        params = {"key": self.gemini_api_key}
        payload = {"model": "models/text-embedding-004", "content": {"parts": [{"text": text}]}}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, params=params, json=payload)
            response.raise_for_status()
            data = response.json()
        values = data["embedding"]["values"]
        if len(values) != EMBEDDING_DIM:
            raise ValueError(f"Expected {EMBEDDING_DIM} dims, got {len(values)}")
        return values

    async def _embed_openai(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.openai_api_key}"},
                json={"model": "text-embedding-3-small", "input": text, "dimensions": EMBEDDING_DIM},
            )
            response.raise_for_status()
            data = response.json()
        values = data["data"][0]["embedding"]
        if len(values) != EMBEDDING_DIM:
            raise ValueError(f"Expected {EMBEDDING_DIM} dims, got {len(values)}")
        return values


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)

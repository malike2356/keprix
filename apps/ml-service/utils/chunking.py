from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    text: str
    index: int
    token_count: int
    metadata: dict[str, Any]


def _fallback_tokens(text: str) -> list[str]:
    return text.split()


def chunk_document(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    metadata: dict[str, Any] | None = None,
    encoding_name: str = "cl100k_base",
) -> list[Chunk]:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    overlap = max(0, min(overlap_tokens, max_tokens - 1))
    try:
        import tiktoken

        encoding = tiktoken.get_encoding(encoding_name)
        encoded = encoding.encode(text)
        decode = encoding.decode
    except Exception:
        encoded = _fallback_tokens(text)
        decode = lambda value: " ".join(value)

    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(encoded):
        end = min(start + max_tokens, len(encoded))
        chunk_tokens = encoded[start:end]
        chunks.append(
            Chunk(
                text=decode(chunk_tokens).strip(),
                index=index,
                token_count=len(chunk_tokens),
                metadata=dict(metadata or {}),
            )
        )
        if end >= len(encoded):
            break
        start = end - overlap
        index += 1
    return chunks

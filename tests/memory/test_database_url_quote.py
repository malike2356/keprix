"""Database URL quoting for RAG / asyncpg."""

from __future__ import annotations

from keprix.memory.rag.indexer import resolve_rag_database_url
from keprix.memory.schema import resolve_database_url


def test_resolve_database_url_quotes_special_password_chars() -> None:
    raw = "postgresql+asyncpg://keprix:p@ss:with+plus@postgres:5432/keprix"
    resolved = resolve_database_url(raw)
    assert resolved.startswith("postgresql://keprix:")
    assert "@postgres:5432/keprix" in resolved
    # Password must be percent-encoded so asyncpg does not treat fragments as host/port
    assert "p%40ss%3Awith%2Bplus" in resolved
    assert resolve_rag_database_url(raw) == resolved


def test_resolve_rag_database_url_reads_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "KEPRIX_DATABASE_URL",
        "postgresql+asyncpg://keprix:TV+Rrdc9lgHVboNu09K1WE5dK2BQRqT@postgres:5432/keprix",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    resolved = resolve_rag_database_url()
    assert "TV%2BRrdc9lgHVboNu09K1WE5dK2BQRqT" in resolved
    assert resolved.endswith("@postgres:5432/keprix")

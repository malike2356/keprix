"""Workspace documents durability smoke tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_document_crud_and_search_memory_mode():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/workspace/documents",
            json={
                "title": "Roadmap",
                "content": "# Roadmap\n\nShip documents phase A.",
                "tags": ["plan"],
                "folder": "product",
            },
        )
        assert created.status_code == 201, created.text
        doc_id = created.json()["id"]

        listed = await client.get("/api/workspace/documents?q=Roadmap")
        assert listed.status_code == 200
        assert any(item["id"] == doc_id for item in listed.json()["items"])

        shared = await client.post(f"/api/workspace/documents/{doc_id}/share")
        assert shared.status_code == 200
        token = shared.json()["share_token"]
        assert token

        public = await client.get(f"/api/workspace/documents/shared/{token}")
        assert public.status_code == 200
        assert public.json()["title"] == "Roadmap"

        exported = await client.get(f"/api/workspace/documents/{doc_id}/export?format=md")
        assert exported.status_code == 200
        assert b"Ship documents" in exported.content

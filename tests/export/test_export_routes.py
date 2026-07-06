"""Export HTTP route tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_create_and_download_export(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/export",
            headers=headers,
            json={
                "title": "Route Test",
                "markdown": "# Hello\n\nWorld",
                "format": "html",
            },
        )
        assert created.status_code == 200
        payload = created.json()
        assert payload["format_returned"] == "html"
        file_id = payload["file_id"]
        assert file_id
        assert payload["file_url"] == f"/api/export/{file_id}"

        download = await client.get(f"/api/export/{file_id}", headers=headers)
        assert download.status_code == 200
        assert "Hello" in download.text

        inline = await client.get(f"/api/export/{file_id}/inline", headers=headers)
        assert inline.status_code == 200
        assert "Hello" in inline.text

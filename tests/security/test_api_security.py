"""API validation integration tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_path_traversal_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/security/validate-path",
            json={"path": "../../etc/passwd"},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agent_output_api_key_redacted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/security/redact",
            json={"text": "key sk-12345678901234567890123456789012"},
        )
    assert response.status_code == 200
    assert "[REDACTED:api_key]" in response.json()["text"]

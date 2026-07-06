"""Review gateway route tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_create_list_and_public_review(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    import keprix.review_gateway.store as review_store_module

    review_store_module._store = None
    headers = {"Authorization": "Bearer test-api-token", "x-workspace-id": "ws-review-test"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/review-gateway/requests",
            headers=headers,
            json={
                "title": "Hazard Log review",
                "context_message": "Please approve",
                "artifact_type": "markdown",
                "artifact_content": "# Hazard Log\n\nNo critical issues.",
                "reviewer_name": "Alice",
                "reviewer_email": "alice@example.com",
                "allowed_actions": ["approve", "reject"],
            },
        )
        assert created.status_code == 200
        payload = created.json()
        review_url = payload["review_url"]
        token = review_url.rsplit("/", 1)[-1]

        listed = await client.get("/api/review-gateway/requests", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()["requests"]) == 1

        page = await client.get(f"/review/{token}")
        assert page.status_code == 200
        assert "Hazard Log review" in page.text

        decided = await client.post(
            f"/review/{token}",
            data={"action": "approve", "reviewer_note": "Looks good", "csrf_token": _csrf_from_html(page.text)},
        )
        assert decided.status_code == 200
        assert "recorded" in decided.text.lower()

        again = await client.get(f"/review/{token}")
        assert again.status_code == 410


def _csrf_from_html(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    end = html.index('"', start)
    return html[start:end]

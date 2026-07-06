"""RAG pipeline HTTP API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.server import create_app
from keprix.api.auth import require_api_auth
from keprix.rag_pipeline.pipeline import get_pipeline_registry


@pytest.fixture(autouse=True)
def disable_database(monkeypatch):
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)


@pytest.fixture
def app():
    application = create_app()

    async def _local_auth() -> str:
        return "local"

    application.dependency_overrides[require_api_auth] = _local_auth
    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_rag_pipeline_api_ingest_and_query(client):
    ingest = await client.post(
        "/api/rag-pipeline/ingest",
        json={
            "user_id": "api-user",
            "source_id": "manual",
            "content": "Building 3 requires weekly HVAC inspection.",
            "pipeline_id": "api-pipeline",
        },
    )
    assert ingest.status_code == 200
    ingest_payload = ingest.json()
    assert ingest_payload["playbook_run_id"]

    query = await client.post(
        "/api/rag-pipeline/query",
        json={
            "user_id": "api-user",
            "question": "What does Building 3 require?",
            "pipeline_id": "api-pipeline",
        },
    )
    assert query.status_code == 200
    payload = query.json()
    assert payload["citations"]
    assert payload["evaluation_id"]

    evals = await client.get("/api/rag-pipeline/evaluations?pipeline_id=api-pipeline")
    assert evals.status_code == 200
    assert evals.json()["evaluations"]

    get_pipeline_registry()._runs.clear()


@pytest.mark.asyncio
async def test_list_rag_connectors_includes_notion(client):
    response = await client.get("/api/rag-pipeline/connectors")
    assert response.status_code == 200
    connectors = response.json()["connectors"]
    notion = next(item for item in connectors if item["id"] == "notion")
    assert "Notion" in notion["description"]


@pytest.mark.asyncio
async def test_ingest_notion_route(client, monkeypatch):
    monkeypatch.setenv("KEPRIX_NOTION_TOKEN", "secret_test_token")

    class FakeConnector:
        def list_documents(self):
            return [{"id": "page-1", "title": "Page 1", "metadata": {}}]

        def fetch_document(self, doc_id: str):
            return {
                "id": doc_id,
                "title": "Page 1",
                "content": "Building 3 HVAC maintenance every Monday.",
                "metadata": {},
            }

    monkeypatch.setattr(
        "keprix.rag_pipeline.routes.get_connector",
        lambda connector_id, **kwargs: FakeConnector(),
    )

    response = await client.post(
        "/api/rag-pipeline/ingest/notion",
        json={
            "pipeline_id": "notion-test",
            "page_ids": ["page-1"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents_ingested"] == 1
    assert payload["run_id"]

    get_pipeline_registry()._runs.clear()

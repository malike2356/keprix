"""Tests for integrations/notion/client.py.

All tests use httpx mock responses - no real Notion API calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from keprix.integrations.notion.client import NotionClient
from keprix.integrations.notion.errors import (
    NotionAuthError,
    NotionNotFoundError,
    NotionRateLimitError,
    NotionValidationError,
)


def _mock_response(status_code: int, body: dict) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )


@pytest.fixture
def client():
    return NotionClient(api_key="secret-key")


@pytest.mark.asyncio
async def test_successful_request_returns_json(client):
    body = {"object": "list", "results": []}
    with patch.object(client._http, "request", new=AsyncMock(
        return_value=_mock_response(200, body)
    )):
        result = await client._request("GET", "/pages/abc")
    assert result["object"] == "list"


@pytest.mark.asyncio
async def test_401_raises_auth_error(client):
    body = {"message": "API token is invalid."}
    with patch.object(client._http, "request", new=AsyncMock(
        return_value=_mock_response(401, body)
    )):
        with pytest.raises(NotionAuthError):
            await client._request("GET", "/pages/abc")


@pytest.mark.asyncio
async def test_404_raises_not_found(client):
    body = {"message": "Could not find page."}
    with patch.object(client._http, "request", new=AsyncMock(
        return_value=_mock_response(404, body)
    )):
        with pytest.raises(NotionNotFoundError):
            await client._request("GET", "/pages/abc")


@pytest.mark.asyncio
async def test_400_raises_validation_error(client):
    body = {"message": "body.page_size should be <= 100"}
    with patch.object(client._http, "request", new=AsyncMock(
        return_value=_mock_response(400, body)
    )):
        with pytest.raises(NotionValidationError):
            await client._request("POST", "/search", json={})


@pytest.mark.asyncio
async def test_sanitize_removes_paths():
    msg = client_inst = NotionClient("k")
    clean = NotionClient._sanitize("Error at /home/user/app/server.js:123 something")
    assert "/home" not in clean
    assert ":123" not in clean


def test_sanitize_leaves_normal_message():
    clean = NotionClient._sanitize("API token is invalid.")
    assert clean == "API token is invalid."


@pytest.mark.asyncio
async def test_search_sends_correct_body(client):
    body = {"object": "list", "results": [], "has_more": False}
    captured = {}

    async def mock_request(method, path, **kwargs):
        captured["method"] = method
        captured["json"] = kwargs.get("json")
        return _mock_response(200, body)

    with patch.object(client._http, "request", new=mock_request):
        await client.search("test query", page_size=10)

    assert captured["method"] == "POST"
    assert captured["json"]["query"] == "test query"
    assert captured["json"]["page_size"] == 10


@pytest.mark.asyncio
async def test_append_blocks_caps_at_100(client):
    body = {"object": "block"}
    captured = {}

    async def mock_request(method, path, **kwargs):
        captured["children_count"] = len(kwargs.get("json", {}).get("children", []))
        return _mock_response(200, body)

    with patch.object(client._http, "request", new=mock_request):
        await client.append_blocks("block-id", children=[{"type": "paragraph"}] * 200)

    assert captured["children_count"] == 100


@pytest.mark.asyncio
async def test_query_database_omits_empty_optional_fields(client):
    body = {"object": "list", "results": []}
    captured = {}

    async def mock_request(method, path, **kwargs):
        captured["json"] = kwargs.get("json", {})
        return _mock_response(200, body)

    with patch.object(client._http, "request", new=mock_request):
        await client.query_database("db-id")

    assert "filter" not in captured["json"]
    assert "sorts" not in captured["json"]


def test_parse_retry_after_from_message():
    client = NotionClient("k")
    assert client._parse_retry_after("retry after 30 seconds") == 30


def test_parse_retry_after_fallback():
    client = NotionClient("k")
    assert client._parse_retry_after("no digits here") == 1

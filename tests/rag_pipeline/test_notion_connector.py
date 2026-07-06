"""Tests for the Notion RAG source connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from keprix.rag_pipeline.connectors.notion import NotionSourceConnector


def _mock_response(payload: dict) -> MagicMock:
    body = json.dumps(payload).encode("utf-8")
    response = MagicMock()
    response.read.return_value = body
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


@pytest.fixture
def notion_connector() -> NotionSourceConnector:
    return NotionSourceConnector("secret_test_token", page_ids=["page-abc"])


def test_list_documents_explicit_page_ids(notion_connector: NotionSourceConnector):
    page_payload = {
        "object": "page",
        "id": "page-abc",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Ops Handbook"}],
            }
        },
    }

    with patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value = _mock_response(page_payload)
        docs = notion_connector.list_documents()

    assert len(docs) == 1
    assert docs[0]["id"] == "page-abc"
    assert docs[0]["title"] == "Ops Handbook"


def test_fetch_document_prefers_markdown(notion_connector: NotionSourceConnector):
    page_payload = {
        "object": "page",
        "id": "page-abc",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Ops Handbook"}],
            }
        },
    }
    markdown_payload = {"markdown": "# Ops Handbook\n\nWeekly HVAC checks."}

    with patch("urllib.request.urlopen") as urlopen:
        urlopen.side_effect = [
            _mock_response(page_payload),
            _mock_response(markdown_payload),
        ]
        fetched = notion_connector.fetch_document("page-abc")

    assert fetched["title"] == "Ops Handbook"
    assert "Weekly HVAC checks" in fetched["content"]


def test_search_list_documents():
    connector = NotionSourceConnector("secret_test_token")
    search_payload = {
        "results": [
            {
                "object": "page",
                "id": "page-search-1",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Search Result"}],
                    }
                },
            }
        ],
        "has_more": False,
    }
    page_payload = {
        "object": "page",
        "id": "page-search-1",
        "properties": {
            "title": {
                "type": "title",
                "title": [{"plain_text": "Search Result"}],
            }
        },
    }

    with patch("urllib.request.urlopen") as urlopen:
        urlopen.side_effect = [
            _mock_response(search_payload),
            _mock_response(page_payload),
        ]
        docs = connector.list_documents()

    assert len(docs) == 1
    assert docs[0]["id"] == "page-search-1"
    assert docs[0]["title"] == "Search Result"

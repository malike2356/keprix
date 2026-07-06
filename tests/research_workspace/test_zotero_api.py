"""Zotero API client tests."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

import pytest

from keprix.research_workspace.citations.zotero_api import ZoteroClient, ZoteroSettingsStore
from keprix.research_workspace.errors import ZoteroAPIError


SAMPLE_ITEM = [
    {
        "key": "ABCD1234",
        "data": {
            "key": "ABCD1234",
            "itemType": "journalArticle",
            "title": "Groundwater monitoring",
            "creators": [{"creatorType": "author", "firstName": "Ada", "lastName": "Lovelace"}],
            "date": "2024",
            "publicationTitle": "Hydrology Journal",
            "DOI": "10.1000/xyz",
            "abstractNote": "Monitoring yields.",
            "tags": [{"tag": "water"}],
            "collections": ["COL1"],
            "citationKey": "lovelace2024ground",
        },
    }
]


def test_zotero_client_normalizes_items():
    client = ZoteroClient(api_key="test-key")

    def fake_urlopen(request, timeout=20):
        payload = json.dumps(SAMPLE_ITEM).encode("utf-8")
        return BytesIO(payload)

    with patch("urllib.request.urlopen", fake_urlopen):
        records = client.list_items(library_type="user", library_id="12345")
    assert len(records) == 1
    record = records[0]
    assert record.citation_key == "lovelace2024ground"
    assert record.title == "Groundwater monitoring"
    assert record.authors == ["Ada Lovelace"]
    assert record.doi == "10.1000/xyz"
    assert record.source == "zotero_web"


def test_zotero_client_raises_on_http_error():
    client = ZoteroClient(api_key="bad")

    class FakeHTTPError(Exception):
        code = 403
        reason = "Forbidden"

    def fake_urlopen(request, timeout=20):
        raise ZoteroAPIError("Zotero API error 403: Forbidden")

    with patch("urllib.request.urlopen", fake_urlopen):
        with pytest.raises(ZoteroAPIError):
            client.list_items(library_type="user", library_id="12345")


def test_settings_store_roundtrip(tmp_path):
    store = ZoteroSettingsStore(tmp_path)
    from keprix.research_workspace.citations.zotero_api import ZoteroSettings

    saved = store.save(ZoteroSettings(mode="web", library_id="999", library_type="user"))
    loaded = store.load()
    assert loaded.library_id == saved.library_id
    assert loaded.mode == "web"

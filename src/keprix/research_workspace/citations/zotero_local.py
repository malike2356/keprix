"""Zotero local connector API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from keprix.research_workspace.citations.models import CitationRecord
from keprix.research_workspace.citations.zotero_api import ZoteroClient
from keprix.research_workspace.errors import ZoteroAPIError


class ZoteroLocalClient(ZoteroClient):
    def __init__(self, *, base_url: str = "http://127.0.0.1:23119") -> None:
        super().__init__(api_key=None, base_url=base_url)

    def list_items(self, *, library_type: str = "user", library_id: str = "0", limit: int = 100) -> list[CitationRecord]:
        payload = self._request(f"/api/{library_type}s/{library_id}/items?limit={limit}")
        records = [self._normalize_item(item) for item in payload]
        for record in records:
            record.source = "zotero_local"
        return records

    def ping(self) -> bool:
        try:
            self._request("/api/users/0/items?limit=1")
            return True
        except ZoteroAPIError:
            return False

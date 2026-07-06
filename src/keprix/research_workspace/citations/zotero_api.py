"""Zotero Web API client and settings store."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from keprix.research_workspace.citations.citation_keys import generate_citation_key
from keprix.research_workspace.citations.models import CitationRecord
from keprix.research_workspace.errors import ResearchWorkspaceError, ZoteroAPIError


@dataclass
class ZoteroSettings:
    mode: str = "web"
    library_id: str | None = None
    library_type: str = "user"
    api_key_vault_id: str | None = None
    vault_user_id: str | None = None
    local_base_url: str = "http://127.0.0.1:23119"
    upload_attachments: bool = False
    obsidian_vault_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZoteroSettings:
        return cls(
            mode=str(data.get("mode") or "web"),
            library_id=data.get("library_id"),
            library_type=str(data.get("library_type") or "user"),
            api_key_vault_id=data.get("api_key_vault_id"),
            vault_user_id=data.get("vault_user_id"),
            local_base_url=str(data.get("local_base_url") or "http://127.0.0.1:23119"),
            upload_attachments=bool(data.get("upload_attachments")),
            obsidian_vault_id=data.get("obsidian_vault_id"),
        )


class ZoteroSettingsStore:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.config_path = workspace_root / "zotero_settings.json"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def load(self) -> ZoteroSettings:
        if not self.config_path.exists():
            return ZoteroSettings()
        return ZoteroSettings.from_dict(json.loads(self.config_path.read_text(encoding="utf-8")))

    def save(self, settings: ZoteroSettings) -> ZoteroSettings:
        self.config_path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
        return settings


class ZoteroClient:
    def __init__(self, *, api_key: str | None = None, base_url: str = "https://api.zotero.org") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"Zotero-API-Version": "3"}
        if self.api_key:
            headers["Zotero-API-Key"] = self.api_key
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ZoteroAPIError(f"Zotero API error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ZoteroAPIError(f"Zotero API unreachable: {exc.reason}") from exc

    def list_items(self, *, library_type: str, library_id: str, limit: int = 100) -> list[CitationRecord]:
        prefix = "users" if library_type == "user" else "groups"
        payload = self._request(f"/{prefix}/{library_id}/items?limit={limit}")
        return [self._normalize_item(item) for item in payload]

    def _normalize_item(self, item: dict[str, Any]) -> CitationRecord:
        data = item.get("data") or {}
        creators = data.get("creators") or []
        authors = [
            " ".join(part for part in [creator.get("firstName"), creator.get("lastName")] if part)
            for creator in creators
            if creator.get("creatorType") in {"author", None}
        ]
        year = None
        date = data.get("date") or ""
        if date[:4].isdigit():
            year = date[:4]
        item_key = str(data.get("key") or item.get("key") or "")
        title = data.get("title") or "Untitled"
        citation_key = data.get("citationKey") or generate_citation_key(
            authors=authors,
            year=year,
            title=title,
            preferred_key=item_key,
        )
        tags = [tag.get("tag") for tag in data.get("tags") or [] if tag.get("tag")]
        collections = [str(value) for value in data.get("collections") or []]
        return CitationRecord(
            item_key=item_key,
            citation_key=citation_key,
            title=title,
            authors=authors,
            year=year,
            publication=data.get("publicationTitle") or data.get("bookTitle"),
            doi=data.get("DOI"),
            url=data.get("url"),
            abstract=data.get("abstractNote"),
            tags=tags,
            collections=collections,
            attachments=[],
            notes=[],
            source="zotero_web",
        )

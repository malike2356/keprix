"""Read-only Notion source connector for RAG pipeline ingestion."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"


def _extract_title(properties: Dict[str, Any] | None) -> str:
    if not properties:
        return "Untitled"
    for prop in properties.values():
        if not isinstance(prop, dict):
            continue
        if prop.get("type") == "title":
            parts = prop.get("title") or []
            text = "".join(
                (piece.get("plain_text") or piece.get("text", {}).get("content") or "")
                for piece in parts
                if isinstance(piece, dict)
            )
            if text.strip():
                return text.strip()
    return "Untitled"


def _blocks_to_text(blocks: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for block in blocks:
        block_type = block.get("type")
        payload = block.get(block_type) if isinstance(block_type, str) else None
        if not isinstance(payload, dict):
            continue
        rich_text = payload.get("rich_text") or []
        text = "".join(
            (piece.get("plain_text") or piece.get("text", {}).get("content") or "")
            for piece in rich_text
            if isinstance(piece, dict)
        )
        if text.strip():
            lines.append(text.strip())
    return "\n\n".join(lines)


class NotionSourceConnector:
    connector_id = "notion"

    def __init__(
        self,
        token: str,
        *,
        page_ids: Optional[List[str]] = None,
        database_ids: Optional[List[str]] = None,
        max_database_rows: int = 500,
    ) -> None:
        self.token = token.strip()
        self.page_ids = [pid.strip() for pid in (page_ids or []) if pid and pid.strip()]
        self.database_ids = [
            did.strip() for did in (database_ids or []) if did and did.strip()
        ]
        self.max_database_rows = max(1, int(max_database_rows))

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{NOTION_API_BASE}{path}"
        data = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        last_error: Exception | None = None
        for attempt in range(4):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < 3:
                    time.sleep(2**attempt)
                    last_error = exc
                    continue
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Notion API {exc.code}: {detail}") from exc
            except Exception as exc:
                last_error = exc
                raise
        if last_error:
            raise last_error
        return {}

    def list_documents(self) -> List[Dict[str, Any]]:
        documents: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for page_id in self.page_ids:
            if page_id in seen:
                continue
            seen.add(page_id)
            documents.append(
                {
                    "id": page_id,
                    "title": page_id,
                    "metadata": {"object": "page", "source": "explicit_page_id"},
                }
            )

        for data_source_id in self.database_ids:
            page_ids = self._list_pages_for_data_source(data_source_id)
            for page_id in page_ids:
                if page_id in seen:
                    continue
                seen.add(page_id)
                documents.append(
                    {
                        "id": page_id,
                        "title": page_id,
                        "metadata": {
                            "object": "page",
                            "data_source_id": data_source_id,
                            "source": "database_query",
                        },
                    }
                )

        if not self.page_ids and not self.database_ids:
            documents.extend(self._search_documents(seen))

        for doc in documents:
            try:
                page = self._request("GET", f"/pages/{doc['id']}")
                doc["title"] = _extract_title(page.get("properties"))
                doc["metadata"]["object"] = page.get("object", doc["metadata"].get("object"))
            except Exception:
                pass

        return documents

    def _search_documents(self, seen: set[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        start_cursor: str | None = None
        while True:
            body: Dict[str, Any] = {"page_size": 100}
            if start_cursor:
                body["start_cursor"] = start_cursor
            payload = self._request("POST", "/search", body=body)
            for item in payload.get("results") or []:
                if not isinstance(item, dict):
                    continue
                obj_type = item.get("object")
                if obj_type not in ("page", "data_source"):
                    continue
                item_id = str(item.get("id") or "")
                if not item_id or item_id in seen:
                    continue
                if obj_type == "data_source":
                    for page_id in self._list_pages_for_data_source(item_id):
                        if page_id in seen:
                            continue
                        seen.add(page_id)
                        results.append(
                            {
                                "id": page_id,
                                "title": _extract_title(item.get("properties")),
                                "metadata": {
                                    "object": "page",
                                    "data_source_id": item_id,
                                    "source": "search_data_source",
                                },
                            }
                        )
                    continue
                seen.add(item_id)
                results.append(
                    {
                        "id": item_id,
                        "title": _extract_title(item.get("properties")),
                        "metadata": {"object": "page", "source": "search"},
                    }
                )
            if not payload.get("has_more"):
                break
            start_cursor = payload.get("next_cursor")
            if not start_cursor:
                break
        return results

    def _list_pages_for_data_source(self, data_source_id: str) -> List[str]:
        page_ids: List[str] = []
        start_cursor: str | None = None
        while len(page_ids) < self.max_database_rows:
            body: Dict[str, Any] = {"page_size": min(100, self.max_database_rows - len(page_ids))}
            if start_cursor:
                body["start_cursor"] = start_cursor
            payload = self._request(
                "POST",
                f"/data_sources/{data_source_id}/query",
                body=body,
            )
            for row in payload.get("results") or []:
                if isinstance(row, dict) and row.get("id"):
                    page_ids.append(str(row["id"]))
                    if len(page_ids) >= self.max_database_rows:
                        break
            if not payload.get("has_more") or len(page_ids) >= self.max_database_rows:
                break
            start_cursor = payload.get("next_cursor")
            if not start_cursor:
                break
        return page_ids

    def fetch_document(self, doc_id: str) -> Dict[str, Any]:
        page_id = doc_id.strip()
        title = page_id
        metadata: Dict[str, Any] = {"object": "page"}

        try:
            page = self._request("GET", f"/pages/{page_id}")
            title = _extract_title(page.get("properties"))
            metadata["object"] = page.get("object", "page")
        except Exception:
            pass

        content = ""
        try:
            markdown_payload = self._request("GET", f"/pages/{page_id}/markdown")
            content = str(markdown_payload.get("markdown") or "").strip()
        except Exception:
            content = ""

        if not content:
            blocks_payload = self._request("GET", f"/blocks/{page_id}/children")
            content = _blocks_to_text(blocks_payload.get("results") or [])

        if not content.strip():
            content = f"(No extractable content for Notion page {page_id})"

        return {
            "id": page_id,
            "title": title,
            "content": content,
            "metadata": metadata,
        }

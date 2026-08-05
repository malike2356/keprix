"""Notion API client: auth, versioning, retry, rate limit, error classification."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from .errors import (
    NotionAuthError,
    NotionNotFoundError,
    NotionRateLimitError,
    NotionServerError,
    NotionTimeoutError,
    NotionValidationError,
)

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION  = "2026-03-11"
MAX_RETRIES     = 3
TIMEOUT_SECONDS = 55.0


class NotionClient:
    """Async Notion API client adapted from OmniRoute's notion/api.ts.

    Handles:
      - Bearer auth with Notion integration token
      - API versioning header
      - Automatic retry with exponential backoff
      - Rate limit handling (respects retry-after)
      - Error classification into typed exceptions
      - Error message sanitisation (removes file paths)
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT_SECONDS,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "NotionClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._http.request(
                    method, path, json=json, params=params
                )

                if response.is_success:
                    return response.json()

                try:
                    error_body = response.json()
                except Exception:
                    error_body = {}

                exc = self._classify_error(response.status_code, error_body)

                if isinstance(exc, NotionRateLimitError):
                    last_error = exc
                    wait = exc.retry_after + (2 ** attempt) * 0.2
                    logger.warning("Notion rate limit; retrying in %.1fs", wait)
                    await asyncio.sleep(wait)
                    continue

                if isinstance(exc, NotionServerError) and attempt < MAX_RETRIES - 1:
                    last_error = exc
                    wait = (2 ** attempt) * 0.5
                    logger.warning("Notion server error; retrying in %.1fs", wait)
                    await asyncio.sleep(wait)
                    continue

                raise exc

            except httpx.TimeoutException:
                raise NotionTimeoutError("Notion API request timed out after 55s")
            except (NotionAuthError, NotionNotFoundError, NotionValidationError):
                raise
            except (NotionRateLimitError, NotionServerError, NotionTimeoutError):
                raise
            except Exception as exc:
                if attempt < MAX_RETRIES - 1:
                    last_error = exc
                    await asyncio.sleep((2 ** attempt) * 0.5)
                    continue
                raise

        raise last_error or NotionServerError("Exhausted all retries")

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def _classify_error(self, status: int, body: dict) -> Exception:
        message = self._sanitize(body.get("message", f"HTTP {status}"))

        if status == 401:
            return NotionAuthError(message)
        if status == 403:
            return NotionAuthError(f"Access denied: {message}")
        if status == 404:
            return NotionNotFoundError(message)
        if status == 409:
            return NotionValidationError(f"Conflict: {message}")
        if status == 429:
            retry_after = self._parse_retry_after(message)
            return NotionRateLimitError(message, retry_after)
        if status == 400:
            return NotionValidationError(message)
        if status >= 500:
            return NotionServerError(message)
        return NotionValidationError(message)

    @staticmethod
    def _sanitize(msg: str) -> str:
        msg = re.sub(r"\s+at\s+\S+", "", msg)
        msg = re.sub(r"/[\w/.\-]+\.[a-z]+:\d+", "", msg)
        return msg[:4096]

    @staticmethod
    def _parse_retry_after(message: str) -> int:
        m = re.search(r"retry after (\d+)", message, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)", message)
        return int(m.group(1)) if m else 1

    # ------------------------------------------------------------------
    # API methods
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        start_cursor: str | None = None,
        page_size: int = 20,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "query": query,
            "page_size": min(page_size, 100),
            "filter": {"value": "page", "property": "object"},
        }
        if start_cursor:
            body["start_cursor"] = start_cursor
        return await self._request("POST", "/search", json=body)

    async def get_page(self, page_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/pages/{page_id}")

    async def list_block_children(
        self,
        block_id: str,
        start_cursor: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": min(page_size, 100)}
        if start_cursor:
            params["start_cursor"] = start_cursor
        return await self._request("GET", f"/blocks/{block_id}/children", params=params)

    async def query_database(
        self,
        database_id: str,
        filter: dict | None = None,
        sorts: list | None = None,
        start_cursor: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"page_size": min(page_size, 100)}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts
        if start_cursor:
            body["start_cursor"] = start_cursor
        return await self._request("POST", f"/databases/{database_id}/query", json=body)

    async def get_database(self, database_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/databases/{database_id}")

    async def append_blocks(
        self,
        block_id: str,
        children: list,
        after: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"children": children[:100]}
        if after:
            body["after"] = after
        return await self._request("PATCH", f"/blocks/{block_id}/children", json=body)

    async def create_page(
        self,
        parent_page_id: str,
        title: str,
        children: list | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]},
            },
        }
        if children:
            body["children"] = children
        return await self._request("POST", "/pages", json=body)

"""Document Vault HTTP helpers for TUI (Prompt 648). Tenant vault only."""

from __future__ import annotations

from typing import Any

from keprix.tui.client import KeprixClient


class DocumentVaultTuiClient:
    """Thin wrapper around /api/document-vault for command palette workflows."""

    def __init__(self, client: KeprixClient, workspace_id: str | None = None) -> None:
        self._client = client
        self.workspace_id = workspace_id or ""

    def _headers(self) -> dict[str, str]:
        headers = self._client._headers()
        if self.workspace_id:
            headers["X-Workspace-Id"] = self.workspace_id
        return headers

    async def list_items(
        self,
        *,
        parent_id: str | None = None,
        q: str | None = None,
        include_trashed: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        await self._client.ensure_auth()
        params: dict[str, Any] = {"limit": limit, "include_trashed": str(include_trashed).lower()}
        if parent_id:
            params["parent_id"] = parent_id
        if q:
            params["q"] = q
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.get(
                f"{self._client.base_url}/api/document-vault/items",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
        return payload if isinstance(payload, dict) else {}

    async def create_folder(self, name: str, *, parent_id: str | None = None) -> dict[str, Any]:
        return await self._post_item({"kind": "folder", "name": name, "parent_id": parent_id})

    async def create_text(
        self,
        name: str,
        content: str = "",
        *,
        parent_id: str | None = None,
        kind: str = "markdown",
    ) -> dict[str, Any]:
        return await self._post_item(
            {"kind": kind, "name": name, "content": content, "parent_id": parent_id}
        )

    async def rename(self, item_id: str, name: str) -> dict[str, Any]:
        return await self._patch_item(item_id, {"name": name})

    async def move(self, item_id: str, parent_id: str | None) -> dict[str, Any]:
        await self._client.ensure_auth()
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{self._client.base_url}/api/document-vault/items/{item_id}/move",
                headers=self._headers(),
                json={"parent_id": parent_id},
            )
            response.raise_for_status()
            return response.json()

    async def trash(self, item_id: str) -> dict[str, Any]:
        await self._client.ensure_auth()
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{self._client.base_url}/api/document-vault/items/{item_id}/trash",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def restore(self, item_id: str) -> dict[str, Any]:
        await self._client.ensure_auth()
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{self._client.base_url}/api/document-vault/items/{item_id}/restore",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def read_content(self, item_id: str) -> dict[str, Any]:
        await self._client.ensure_auth()
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.get(
                f"{self._client.base_url}/api/document-vault/items/{item_id}/content",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def export(self, item_id: str, format_name: str) -> bytes:
        await self._client.ensure_auth()
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as http:
            response = await http.post(
                f"{self._client.base_url}/api/document-vault/items/{item_id}/export",
                headers=self._headers(),
                json={"format": format_name},
            )
            response.raise_for_status()
            return response.content

    async def _post_item(self, body: dict[str, Any]) -> dict[str, Any]:
        await self._client.ensure_auth()
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{self._client.base_url}/api/document-vault/items",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def _patch_item(self, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
        await self._client.ensure_auth()
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.patch(
                f"{self._client.base_url}/api/document-vault/items/{item_id}",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()


def format_vault_listing(payload: dict[str, Any]) -> str:
    items = payload.get("items") or []
    if not items:
        return "Document Vault: empty (tenant vault; not host filesystem)."
    lines = ["Document Vault (tenant)", f"count={len(items)}"]
    for row in items:
        kind = row.get("kind") or "?"
        name = row.get("name") or "?"
        item_id = row.get("id") or "?"
        trashed = " [trash]" if row.get("trashed") or row.get("trashed_at") else ""
        lines.append(f"- [{kind}] {name} ({item_id}){trashed}")
    return "\n".join(lines)


__all__ = ["DocumentVaultTuiClient", "format_vault_listing"]

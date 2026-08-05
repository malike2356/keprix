"""Encrypted credential vault store."""

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from keprix.security.crypto import decrypt_aes_gcm, derive_key, encrypt_aes_gcm


class VaultStore:
    async def create(
        self,
        *,
        user_id: str,
        label: str,
        category: str,
        username: str | None,
        value: str,
        url: str | None,
        tags: list[str],
        encryption_key: bytes,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def list_items(self, user_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def get_item(self, user_id: str, item_id: str, *, encryption_key: bytes) -> dict[str, Any]:
        raise NotImplementedError

    async def update(
        self,
        user_id: str,
        item_id: str,
        *,
        encryption_key: bytes,
        **fields: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def delete(self, user_id: str, item_id: str) -> None:
        raise NotImplementedError


class InMemoryVaultStore(VaultStore):
    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    async def create(
        self,
        *,
        user_id: str,
        label: str,
        category: str,
        username: str | None,
        value: str,
        url: str | None,
        tags: list[str],
        encryption_key: bytes,
    ) -> dict[str, Any]:
        item_id = str(uuid4())
        encrypted = encrypt_aes_gcm(value.encode("utf-8"), encryption_key)
        try:
            from keprix.tenancy.isolation import current_tenant_id

            tenant_tag = f"tenant:{current_tenant_id()}"
            if tenant_tag not in tags:
                tags = [*tags, tenant_tag]
        except Exception:
            pass
        item = {
            "id": item_id,
            "user_id": user_id,
            "label": label,
            "category": category,
            "username": username,
            "value_encrypted": encrypted,
            "url": url,
            "tags": tags,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        self._items.append(item)
        return self._public_item(item)

    async def list_items(self, user_id: str) -> list[dict[str, Any]]:
        return [self._public_item(item) for item in self._items if item["user_id"] == user_id]

    async def get_item(self, user_id: str, item_id: str, *, encryption_key: bytes) -> dict[str, Any]:
        item = self._require_item(user_id, item_id)
        value = decrypt_aes_gcm(item["value_encrypted"], encryption_key).decode("utf-8")
        public = self._public_item(item)
        public["value"] = value
        return public

    async def update(
        self,
        user_id: str,
        item_id: str,
        *,
        encryption_key: bytes,
        **fields: Any,
    ) -> dict[str, Any]:
        item = self._require_item(user_id, item_id)
        for key in ("label", "category", "username", "url", "tags"):
            if key in fields and fields[key] is not None:
                item[key] = fields[key]
        if "value" in fields and fields["value"] is not None:
            item["value_encrypted"] = encrypt_aes_gcm(str(fields["value"]).encode("utf-8"), encryption_key)
        item["updated_at"] = datetime.now(timezone.utc)
        return self._public_item(item)

    async def delete(self, user_id: str, item_id: str) -> None:
        self._items = [item for item in self._items if not (item["user_id"] == user_id and item["id"] == item_id)]

    def _require_item(self, user_id: str, item_id: str) -> dict[str, Any]:
        for item in self._items:
            if item["user_id"] == user_id and item["id"] == item_id:
                return item
        raise KeyError(item_id)

    @staticmethod
    def _public_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "user_id": item["user_id"],
            "label": item["label"],
            "category": item["category"],
            "username": item.get("username"),
            "url": item.get("url"),
            "tags": item.get("tags") or [],
            "created_at": item["created_at"].isoformat() if item.get("created_at") else None,
            "updated_at": item["updated_at"].isoformat() if item.get("updated_at") else None,
        }


def derive_vault_key(master_password: str, *, user_id: str) -> bytes:
    salt = f"keprix-vault:{user_id}".encode("utf-8")
    return derive_key(master_password, salt)


vault_store = InMemoryVaultStore()

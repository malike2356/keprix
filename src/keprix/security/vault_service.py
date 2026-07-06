"""AES-256-GCM vault for encrypted credential storage."""

from __future__ import annotations

import json
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _vault_key() -> bytes:
    raw = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not raw:
        raw = "keprix-dev-vault-key-change-me"
    if len(raw) >= 32:
        return raw.encode()[:32]
    return (raw * 32).encode()[:32]


def _encrypt_bytes(plaintext: bytes) -> bytes:
    key = _vault_key()
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def _decrypt_bytes(blob: bytes) -> bytes:
    key = _vault_key()
    nonce, ciphertext = blob[:12], blob[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


@dataclass
class VaultItem:
    id: str
    user_id: str
    label: str
    category: str
    username: str | None
    url: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    _value: str | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "category": self.category,
            "username": self.username,
            "url": self.url,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class VaultService:
    """In-memory vault with optional PostgreSQL backing via repository hook."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[VaultItem, bytes]] = {}
        self._unlocked = True

    async def create_item(
        self,
        user_id: str,
        *,
        label: str,
        value: str,
        category: str = "password",
        username: str | None = None,
        url: str | None = None,
        tags: list[str] | None = None,
    ) -> VaultItem:
        item_id = str(uuid.uuid4())
        now = _utcnow()
        item = VaultItem(
            id=item_id,
            user_id=user_id,
            label=label,
            category=category,
            username=username,
            url=url,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            _value=value,
        )
        self._items[item_id] = (item, _encrypt_bytes(value.encode()))
        await _persist_vault_item(item, self._items[item_id][1])
        return item

    async def get_item(self, item_id: str, user_id: str, *, decrypt: bool = False) -> VaultItem | None:
        row = self._items.get(item_id)
        if row is None:
            row = await _load_vault_item(item_id, user_id)
            if row:
                self._items[item_id] = row
        if row is None:
            return None
        item, blob = row
        if item.user_id != user_id:
            return None
        if decrypt:
            item._value = _decrypt_bytes(blob).decode()
        return item

    async def list_items(self, user_id: str, *, category: str | None = None) -> list[VaultItem]:
        db_items = await _list_vault_items(user_id, category=category)
        for item, blob in db_items:
            self._items[item.id] = (item, blob)
        items = [item for item, _ in self._items.values() if item.user_id == user_id]
        if category:
            items = [i for i in items if i.category == category]
        return sorted(items, key=lambda i: i.label.lower())

    async def delete_item(self, item_id: str, user_id: str) -> bool:
        item = await self.get_item(item_id, user_id)
        if item is None:
            return False
        self._items.pop(item_id, None)
        await _delete_vault_item(item_id, user_id)
        return True

    async def store_oauth_bundle(
        self,
        user_id: str,
        *,
        provider: str,
        label: str,
        tokens: dict[str, Any],
    ) -> str:
        item = await self.create_item(
            user_id,
            label=label,
            value=json.dumps(tokens),
            category="oauth_token",
            tags=[provider],
        )
        return item.id

    async def get_oauth_bundle(self, vault_item_id: str, user_id: str) -> dict[str, Any]:
        item = await self.get_item(vault_item_id, user_id, decrypt=True)
        if item is None or not item._value:
            return {}
        return json.loads(item._value)

    async def update_oauth_bundle(
        self, vault_item_id: str, user_id: str, tokens: dict[str, Any]
    ) -> None:
        item = await self.get_item(vault_item_id, user_id)
        if item is None:
            return
        blob = _encrypt_bytes(json.dumps(tokens).encode())
        item.updated_at = _utcnow()
        self._items[vault_item_id] = (item, blob)
        await _persist_vault_item(item, blob)


_vault: VaultService | None = None


def get_vault_service() -> VaultService:
    global _vault
    if _vault is None:
        _vault = VaultService()
    return _vault


def reset_vault_service() -> None:
    global _vault
    _vault = VaultService()


async def _persist_vault_item(item: VaultItem, blob: bytes) -> None:
    from keprix.db.vault_repo import persist_vault_item

    await persist_vault_item(item, blob)


async def _load_vault_item(item_id: str, user_id: str) -> tuple[VaultItem, bytes] | None:
    from keprix.db.vault_repo import load_vault_item

    return await load_vault_item(item_id, user_id)


async def _list_vault_items(
    user_id: str, *, category: str | None = None
) -> list[tuple[VaultItem, bytes]]:
    from keprix.db.vault_repo import list_vault_items

    return await list_vault_items(user_id, category=category)


async def _delete_vault_item(item_id: str, user_id: str) -> None:
    from keprix.db.vault_repo import delete_vault_item

    await delete_vault_item(item_id, user_id)


class VaultClient:
    """Compatibility wrapper used by legacy bootstrap imports."""

    def get(self, key: str) -> str | None:
        return os.environ.get(key)

    def set(self, key: str, value: str) -> None:
        return None

    def delete(self, key: str) -> None:
        return None


vault = VaultClient()

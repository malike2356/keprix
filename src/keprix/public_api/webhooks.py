"""Signed webhook management for developer integrations."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bcrypt
import httpx

from keprix.public_api.schemas import WebhookCreateRequest, WebhookRecord

logger = logging.getLogger(__name__)


def _webhooks_file() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home()) / "developer" / "webhooks.json"
    except Exception:
        return Path.home() / ".keprix" / "developer" / "webhooks.json"


def _hash_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class WebhookStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _webhooks_file()
        self._secrets: dict[str, str] = {}

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, rows: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def create(self, body: WebhookCreateRequest) -> tuple[WebhookRecord, str]:
        webhook_id = str(uuid.uuid4())
        secret = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": webhook_id,
            "workspace_id": body.workspace_id,
            "url": body.url,
            "secret_hash": _hash_secret(secret),
            "signing_secret": secret,
            "events": body.events,
            "created_at": now,
            "disabled_at": None,
        }
        rows = self._load()
        rows.append(row)
        self._save(rows)
        self._secrets[webhook_id] = secret
        return self._to_record(row), secret

    def list_webhooks(self, workspace_id: str | None = None) -> list[WebhookRecord]:
        rows = self._load()
        result = []
        for row in rows:
            if workspace_id and row.get("workspace_id") != workspace_id:
                continue
            result.append(self._to_record(row))
        return result

    def get_signing_secret(self, webhook_id: str) -> str | None:
        cached = self._secrets.get(webhook_id)
        if cached:
            return cached
        for row in self._load():
            if row["id"] == webhook_id:
                secret = row.get("signing_secret")
                if secret:
                    self._secrets[webhook_id] = secret
                return secret
        return None

    def get_secret_for_test(self, webhook_id: str) -> str | None:
        return self.get_signing_secret(webhook_id)

    def _to_record(self, row: dict[str, Any]) -> WebhookRecord:
        return WebhookRecord(
            id=row["id"],
            url=row["url"],
            events=list(row.get("events") or []),
            workspace_id=row.get("workspace_id", "default"),
            created_at=row.get("created_at", ""),
            disabled=bool(row.get("disabled_at")),
        )


_store: WebhookStore | None = None


def get_webhook_store() -> WebhookStore:
    global _store
    if _store is None:
        _store = WebhookStore()
    return _store


def sign_payload(secret: str, payload: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    expected = sign_payload(secret, payload)
    return hmac.compare_digest(expected, signature)


async def dispatch_webhook_event(
    workspace_id: str,
    event: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    store = get_webhook_store()
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    deliveries: list[dict[str, Any]] = []

    for row in store._load():
        if row.get("disabled_at"):
            continue
        if row.get("workspace_id", "default") != workspace_id:
            continue
        events = list(row.get("events") or [])
        if event not in events and "*" not in events:
            continue
        secret = store.get_signing_secret(row["id"])
        if not secret:
            continue
        signature = sign_payload(secret, body)
        headers = {
            "Content-Type": "application/json",
            "X-Keprix-Event": event,
            "X-Keprix-Signature": signature,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(row["url"], content=body, headers=headers)
            deliveries.append(
                {
                    "webhook_id": row["id"],
                    "status_code": response.status_code,
                    "ok": response.status_code < 400,
                }
            )
        except Exception as exc:
            logger.warning("Webhook delivery failed for %s: %s", row["id"], exc)
            deliveries.append({"webhook_id": row["id"], "ok": False, "error": str(exc)[:200]})
    return deliveries

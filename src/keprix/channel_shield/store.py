"""Channel Shield store with optional durable Postgres/SQLite backend."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.channel_shield.config import load_channel_shield_config
from keprix.channel_shield.crypto_store import destroy_raw_blob, sha256_hex, write_raw_blob
from keprix.channel_shield.durable import DurableBackend, durable_enabled
from keprix.channel_shield.types import MessageStatus, ShieldEnvelope, Verdict


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _utcnow()


@dataclass
class ProtectionRecord:
    id: str
    user_id: str
    channel: str
    label: str
    protection_key: str
    config: dict[str, Any]
    enabled: bool
    verified: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel": self.channel,
            "label": self.label,
            "protection_key": self.protection_key,
            "config": dict(self.config),
            "enabled": self.enabled,
            "verified": self.verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class MessageRecord:
    id: str
    protection_id: str
    user_id: str
    channel: str
    external_message_id: str
    conversation_id: str
    from_addr: str
    to_addrs: list[str]
    subject: str
    text_preview: str
    status: str
    verdict: str | None
    envelope: dict[str, Any]
    report: dict[str, Any]
    safe_summary: str | None
    raw_blob_id: str | None
    scout_ids: list[str]
    created_at: datetime
    updated_at: datetime
    agent_safe_content: dict[str, Any] = field(default_factory=dict)
    policy_label: str | None = None
    raw_evidence_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "protection_id": self.protection_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "external_message_id": self.external_message_id,
            "conversation_id": self.conversation_id,
            "from": self.from_addr,
            "to": list(self.to_addrs),
            "subject": self.subject,
            "text_preview": self.text_preview,
            "status": self.status,
            "verdict": self.verdict,
            "envelope": dict(self.envelope),
            "report": dict(self.report),
            "safe_summary": self.safe_summary,
            "raw_blob_id": self.raw_blob_id,
            "scout_ids": list(self.scout_ids),
            "agent_safe_content": dict(self.agent_safe_content),
            "policy_label": self.policy_label,
            "raw_evidence_ref": self.raw_evidence_ref,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AttachmentRecord:
    id: str
    message_id: str
    filename: str
    content_type: str
    size: int
    sha256: str
    storage_uri: str
    blob_id: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "sha256": self.sha256,
            "storage_uri": self.storage_uri,
            "blob_id": self.blob_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EventRecord:
    id: str
    message_id: str | None
    protection_id: str | None
    event_type: str
    payload: dict[str, Any]
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "protection_id": self.protection_id,
            "event_type": self.event_type,
            "payload": dict(self.payload),
            "created_at": self.created_at.isoformat(),
        }


class ChannelShieldStore:
    def __init__(self, *, durable: bool | None = None) -> None:
        self._lock = asyncio.Lock()
        self.protections: dict[str, ProtectionRecord] = {}
        self.messages: dict[str, MessageRecord] = {}
        self.attachments: dict[str, AttachmentRecord] = {}
        self.events: list[EventRecord] = []
        self.deliveries: list[dict[str, Any]] = []
        self.summaries: list[dict[str, Any]] = []
        self.agent_blocks: list[dict[str, Any]] = []
        self.approval_requests: list[dict[str, Any]] = []
        self.agent_policies: dict[str, dict[str, Any]] = {}
        self.memory_blocks: list[dict[str, Any]] = []
        use_durable = durable_enabled() if durable is None else durable
        self._backend: DurableBackend | None = DurableBackend() if use_durable else None
        self._loaded = False

    async def ensure_loaded(self) -> None:
        if self._loaded or self._backend is None:
            self._loaded = True
            return
        async with self._lock:
            if self._loaded:
                return
            snapshot = await self._backend.load_snapshot()
            for row in snapshot.get("protections") or []:
                rec = ProtectionRecord(
                    id=str(row["id"]),
                    user_id=str(row["user_id"]),
                    channel=str(row["channel"]),
                    label=str(row["label"]),
                    protection_key=str(row["protection_key"]),
                    config=dict(row.get("config") or {}),
                    enabled=bool(row.get("enabled", True)),
                    verified=bool(row.get("verified")),
                    created_at=_parse_dt(row.get("created_at")),
                    updated_at=_parse_dt(row.get("updated_at")),
                )
                self.protections[rec.id] = rec
            for row in snapshot.get("messages") or []:
                rec = MessageRecord(
                    id=str(row["id"]),
                    protection_id=str(row["protection_id"]),
                    user_id=str(row["user_id"]),
                    channel=str(row["channel"]),
                    external_message_id=str(row["external_message_id"]),
                    conversation_id=str(row.get("conversation_id") or ""),
                    from_addr=str(row.get("from_addr") or ""),
                    to_addrs=list(row.get("to_addrs") or []),
                    subject=str(row.get("subject") or ""),
                    text_preview=str(row.get("text_preview") or ""),
                    status=str(row["status"]),
                    verdict=row.get("verdict"),
                    envelope=dict(row.get("envelope") or {}),
                    report=dict(row.get("report") or {}),
                    safe_summary=row.get("safe_summary"),
                    raw_blob_id=row.get("raw_blob_id"),
                    scout_ids=list(row.get("scout_ids") or []),
                    created_at=_parse_dt(row.get("created_at")),
                    updated_at=_parse_dt(row.get("updated_at")),
                    agent_safe_content=dict(row.get("agent_safe_content") or {}),
                    policy_label=row.get("policy_label"),
                    raw_evidence_ref=row.get("raw_evidence_ref"),
                )
                self.messages[rec.id] = rec
            for row in snapshot.get("attachments") or []:
                rec = AttachmentRecord(
                    id=str(row["id"]),
                    message_id=str(row["message_id"]),
                    filename=str(row["filename"]),
                    content_type=str(row.get("content_type") or ""),
                    size=int(row.get("size") or 0),
                    sha256=str(row["sha256"]),
                    storage_uri=str(row["storage_uri"]),
                    blob_id=row.get("blob_id"),
                    created_at=_parse_dt(row.get("created_at")),
                )
                self.attachments[rec.id] = rec
            for row in snapshot.get("events") or []:
                event = EventRecord(
                    id=str(row["id"]),
                    message_id=row.get("message_id"),
                    protection_id=row.get("protection_id"),
                    event_type=str(row["event_type"]),
                    payload=dict(row.get("payload") or {}),
                    created_at=_parse_dt(row.get("created_at")),
                )
                self.events.append(event)
                if event.event_type == "agent.blocked":
                    item = {
                        "id": event.id,
                        "action": (event.payload or {}).get("action"),
                        "agentId": (event.payload or {}).get("agentId"),
                        "messageId": event.message_id,
                        "reason": (event.payload or {}).get("reason"),
                        "payload": dict(event.payload or {}),
                        "createdAt": event.created_at.isoformat(),
                    }
                    self.agent_blocks.append(item)
                    if (event.payload or {}).get("action") == "memory":
                        self.memory_blocks.append(item)
                if event.event_type == "agent.approval_requested":
                    self.approval_requests.append(dict(event.payload or {}))
            self._loaded = True

    def _protection_row(self, record: ProtectionRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "user_id": record.user_id,
            "channel": record.channel,
            "label": record.label,
            "protection_key": record.protection_key,
            "config": dict(record.config),
            "enabled": record.enabled,
            "verified": record.verified,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def _message_row(self, message: MessageRecord) -> dict[str, Any]:
        return {
            "id": message.id,
            "protection_id": message.protection_id,
            "user_id": message.user_id,
            "channel": message.channel,
            "external_message_id": message.external_message_id,
            "conversation_id": message.conversation_id,
            "from_addr": message.from_addr,
            "to_addrs": list(message.to_addrs),
            "subject": message.subject,
            "text_preview": message.text_preview,
            "status": message.status,
            "verdict": message.verdict,
            "envelope": dict(message.envelope),
            "report": dict(message.report),
            "safe_summary": message.safe_summary,
            "raw_blob_id": message.raw_blob_id,
            "scout_ids": list(message.scout_ids),
            "agent_safe_content": dict(message.agent_safe_content),
            "policy_label": message.policy_label,
            "raw_evidence_ref": message.raw_evidence_ref,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
        }

    async def create_protection(
        self,
        user_id: str,
        *,
        channel: str,
        label: str,
        protection_key: str,
        config: dict[str, Any] | None = None,
    ) -> ProtectionRecord:
        await self.ensure_loaded()
        now = _utcnow()
        record = ProtectionRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            channel=channel,
            label=label or f"{channel} protection",
            protection_key=protection_key,
            config=dict(config or {}),
            enabled=True,
            verified=False,
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self.protections[record.id] = record
        if self._backend is not None:
            await self._backend.upsert_protection(self._protection_row(record))
        await self.add_event(
            None,
            record.id,
            "protection.created",
            {"channel": channel, "protection_key": protection_key},
        )
        return record

    async def list_protections(
        self, user_id: str, *, channel: str | None = None
    ) -> list[ProtectionRecord]:
        await self.ensure_loaded()
        items = [p for p in self.protections.values() if p.user_id == user_id]
        if channel:
            items = [p for p in items if p.channel == channel]
        return sorted(items, key=lambda p: p.created_at, reverse=True)

    async def get_protection(
        self, protection_id: str, user_id: str | None = None
    ) -> ProtectionRecord | None:
        await self.ensure_loaded()
        record = self.protections.get(protection_id)
        if record is None:
            return None
        if user_id is not None and record.user_id != user_id:
            return None
        return record

    async def find_protection_by_key(
        self, channel: str, protection_key: str
    ) -> ProtectionRecord | None:
        await self.ensure_loaded()
        for record in self.protections.values():
            if (
                record.channel == channel
                and record.protection_key == protection_key
                and record.enabled
            ):
                return record
        return None

    async def update_protection(
        self, protection_id: str, user_id: str, patch: dict[str, Any]
    ) -> ProtectionRecord | None:
        record = await self.get_protection(protection_id, user_id)
        if record is None:
            return None
        if "label" in patch and patch["label"] is not None:
            record.label = str(patch["label"])
        if "enabled" in patch and patch["enabled"] is not None:
            record.enabled = bool(patch["enabled"])
        if "config" in patch and isinstance(patch["config"], dict):
            record.config = {**record.config, **patch["config"]}
        if "verified" in patch and patch["verified"] is not None:
            record.verified = bool(patch["verified"])
        if "protection_key" in patch and patch["protection_key"]:
            record.protection_key = str(patch["protection_key"])
        record.updated_at = _utcnow()
        if self._backend is not None:
            await self._backend.upsert_protection(self._protection_row(record))
        return record

    async def delete_protection(self, protection_id: str, user_id: str) -> bool:
        record = await self.get_protection(protection_id, user_id)
        if record is None:
            return False
        async with self._lock:
            del self.protections[protection_id]
        if self._backend is not None:
            await self._backend.delete_protection(protection_id)
        return True

    async def store_raw(self, data: bytes) -> tuple[str, str]:
        cfg = load_channel_shield_config()
        blob_id = str(uuid.uuid4())
        uri = write_raw_blob(cfg.raw_store_dir, blob_id, data)
        return blob_id, uri

    async def ingest_envelope(
        self,
        user_id: str,
        envelope: ShieldEnvelope,
        *,
        raw_bytes: bytes | None = None,
    ) -> MessageRecord:
        await self.ensure_loaded()
        blob_id = None
        raw_uri = envelope.raw_storage_uri
        if raw_bytes is not None:
            blob_id, raw_uri = await self.store_raw(raw_bytes)
            envelope.raw_storage_uri = raw_uri

        preview = (envelope.text or "")[:240]
        now = _utcnow()
        message = MessageRecord(
            id=str(uuid.uuid4()),
            protection_id=envelope.protection_id,
            user_id=user_id,
            channel=envelope.channel,
            external_message_id=envelope.external_message_id,
            conversation_id=envelope.conversation_id,
            from_addr=envelope.from_addr,
            to_addrs=list(envelope.to_addrs),
            subject=envelope.subject,
            text_preview=preview,
            status=MessageStatus.PENDING.value,
            verdict=None,
            envelope=envelope.to_dict(),
            report={},
            safe_summary=None,
            raw_blob_id=blob_id,
            scout_ids=[],
            created_at=now,
            updated_at=now,
            agent_safe_content={},
            policy_label=None,
            raw_evidence_ref=raw_uri or None,
        )
        async with self._lock:
            self.messages[message.id] = message
            for att in envelope.attachments:
                att_rec = AttachmentRecord(
                    id=att.id or str(uuid.uuid4()),
                    message_id=message.id,
                    filename=att.filename,
                    content_type=att.content_type,
                    size=att.size,
                    sha256=att.sha256 or sha256_hex(b""),
                    storage_uri=att.storage_uri,
                    blob_id=None,
                    created_at=now,
                )
                self.attachments[att_rec.id] = att_rec
        if self._backend is not None:
            await self._backend.upsert_message(self._message_row(message))
            for att_rec in [
                a for a in self.attachments.values() if a.message_id == message.id
            ]:
                await self._backend.upsert_attachment(
                    {
                        "id": att_rec.id,
                        "message_id": att_rec.message_id,
                        "filename": att_rec.filename,
                        "content_type": att_rec.content_type,
                        "size": att_rec.size,
                        "sha256": att_rec.sha256,
                        "storage_uri": att_rec.storage_uri,
                        "blob_id": att_rec.blob_id,
                        "created_at": att_rec.created_at,
                    }
                )
        await self.add_event(
            message.id,
            envelope.protection_id,
            "message.accepted",
            {"channel": envelope.channel, "external_message_id": envelope.external_message_id},
        )
        return message

    async def update_message(
        self, message_id: str, **fields: Any
    ) -> MessageRecord | None:
        await self.ensure_loaded()
        message = self.messages.get(message_id)
        if message is None:
            return None
        for key, value in fields.items():
            if hasattr(message, key):
                setattr(message, key, value)
        message.updated_at = _utcnow()
        if self._backend is not None:
            await self._backend.upsert_message(self._message_row(message))
        return message

    async def get_message(
        self, message_id: str, user_id: str | None = None
    ) -> MessageRecord | None:
        await self.ensure_loaded()
        message = self.messages.get(message_id)
        if message is None:
            return None
        if user_id is not None and message.user_id != user_id:
            return None
        return message

    async def list_messages(
        self,
        user_id: str,
        *,
        channel: str | None = None,
        status: str | None = None,
        verdict: str | None = None,
        limit: int = 100,
    ) -> list[MessageRecord]:
        await self.ensure_loaded()
        items = [m for m in self.messages.values() if m.user_id == user_id]
        if channel:
            items = [m for m in items if m.channel == channel]
        if status:
            items = [m for m in items if m.status == status]
        if verdict:
            items = [m for m in items if m.verdict == verdict]
        items = sorted(items, key=lambda m: m.created_at, reverse=True)
        return items[:limit]

    async def list_attachments(self, message_id: str) -> list[AttachmentRecord]:
        return [a for a in self.attachments.values() if a.message_id == message_id]

    async def add_event(
        self,
        message_id: str | None,
        protection_id: str | None,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        await self.ensure_loaded()
        event = EventRecord(
            id=str(uuid.uuid4()),
            message_id=message_id,
            protection_id=protection_id,
            event_type=event_type,
            payload=dict(payload or {}),
            created_at=_utcnow(),
        )
        async with self._lock:
            self.events.append(event)
        if self._backend is not None:
            await self._backend.insert_event(
                {
                    "id": event.id,
                    "message_id": event.message_id,
                    "protection_id": event.protection_id,
                    "event_type": event.event_type,
                    "payload": dict(event.payload),
                    "created_at": event.created_at,
                }
            )
        return event

    async def list_events(
        self, *, message_id: str | None = None, limit: int = 200
    ) -> list[EventRecord]:
        await self.ensure_loaded()
        items = self.events
        if message_id:
            items = [e for e in items if e.message_id == message_id]
        return list(reversed(items[-limit:]))

    async def record_delivery(
        self, message_id: str, channel: str, payload: dict[str, Any]
    ) -> None:
        self.deliveries.append(
            {
                "message_id": message_id,
                "channel": channel,
                "payload": payload,
                "at": _utcnow().isoformat(),
            }
        )
        await self.add_event(message_id, None, "message.delivered", {"channel": channel})

    async def record_summary(
        self, message_id: str, channel: str, summary: str, payload: dict[str, Any]
    ) -> None:
        self.summaries.append(
            {
                "message_id": message_id,
                "channel": channel,
                "summary": summary,
                "payload": payload,
                "at": _utcnow().isoformat(),
            }
        )
        await self.add_event(
            message_id,
            None,
            "message.safe_summary",
            {"channel": channel, "summary": summary[:500]},
        )

    async def destroy_message(self, message_id: str, user_id: str) -> bool:
        message = await self.get_message(message_id, user_id)
        if message is None:
            return False
        cfg = load_channel_shield_config()
        if message.raw_blob_id:
            destroy_raw_blob(cfg.raw_store_dir, message.raw_blob_id)
        message.status = MessageStatus.DESTROYED.value
        message.policy_label = "destroyed"
        message.envelope = {"redacted": True}
        message.text_preview = "[destroyed]"
        message.agent_safe_content = {
            "policyLabel": "destroyed",
            "text": "",
            "subject": "",
            "allowedActions": [],
            "rawEvidenceRef": "",
        }
        message.updated_at = _utcnow()
        if self._backend is not None:
            await self._backend.upsert_message(self._message_row(message))
        await self.add_event(message_id, message.protection_id, "message.destroyed", {})
        return True

    async def record_agent_block(
        self,
        *,
        action: str,
        agent_id: str,
        message_id: str | None,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item = {
            "id": str(uuid.uuid4()),
            "action": action,
            "agentId": agent_id,
            "messageId": message_id,
            "reason": reason,
            "payload": dict(payload or {}),
            "createdAt": _utcnow().isoformat(),
        }
        async with self._lock:
            self.agent_blocks.append(item)
            if action == "memory":
                self.memory_blocks.append(item)
        await self.add_event(
            message_id,
            None,
            "agent.blocked",
            {"action": action, "agentId": agent_id, "reason": reason},
        )
        return item

    async def list_agent_blocks(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self.agent_blocks[-limit:]))

    async def list_memory_blocks(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self.memory_blocks[-limit:]))

    async def add_approval_request(self, request: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            self.approval_requests.append(request)
        await self.add_event(
            request.get("messageId"),
            None,
            "agent.approval_requested",
            request,
        )
        return request

    async def list_approval_requests(
        self, *, status: str | None = "pending", limit: int = 50
    ) -> list[dict[str, Any]]:
        items = self.approval_requests
        if status:
            items = [r for r in items if r.get("status") == status]
        return list(reversed(items[-limit:]))

    def reset(self) -> None:
        self.protections.clear()
        self.messages.clear()
        self.attachments.clear()
        self.events.clear()
        self.deliveries.clear()
        self.summaries.clear()
        self.agent_blocks.clear()
        self.approval_requests.clear()
        self.agent_policies.clear()
        self.memory_blocks.clear()


_STORE: ChannelShieldStore | None = None


def get_channel_shield_store() -> ChannelShieldStore:
    global _STORE
    if _STORE is None:
        # Tests set CHANNEL_SHIELD_STORE=memory; production defaults to durable.
        force_memory = (os.environ.get("CHANNEL_SHIELD_STORE") or "").strip().lower() in {
            "memory",
            "mem",
            "inmemory",
        }
        _STORE = ChannelShieldStore(durable=not force_memory)
    return _STORE


def reset_channel_shield_store() -> None:
    global _STORE
    if _STORE is not None:
        _STORE.reset()
    # Tests always get an isolated in-memory store.
    _STORE = ChannelShieldStore(durable=False)

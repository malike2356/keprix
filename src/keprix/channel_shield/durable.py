"""Durable Channel Shield backend: Postgres when available, else SQLite under data dir."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from keprix.channel_shield.models import (
    ChannelShieldAttachmentRow,
    ChannelShieldEventRow,
    ChannelShieldMessageRow,
    ChannelShieldProtectionRow,
)

logger = logging.getLogger(__name__)

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_shield_protections (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    label TEXT NOT NULL,
    protection_key TEXT NOT NULL,
    config TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cs_prot_user_channel
    ON channel_shield_protections(user_id, channel);
CREATE INDEX IF NOT EXISTS ix_cs_prot_key
    ON channel_shield_protections(channel, protection_key);

CREATE TABLE IF NOT EXISTS channel_shield_messages (
    id TEXT PRIMARY KEY,
    protection_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    external_message_id TEXT NOT NULL,
    conversation_id TEXT,
    from_addr TEXT,
    to_addrs TEXT NOT NULL DEFAULT '[]',
    subject TEXT,
    text_preview TEXT,
    status TEXT NOT NULL,
    verdict TEXT,
    envelope TEXT NOT NULL DEFAULT '{}',
    report TEXT NOT NULL DEFAULT '{}',
    safe_summary TEXT,
    raw_blob_id TEXT,
    scout_ids TEXT NOT NULL DEFAULT '[]',
    agent_safe_content TEXT NOT NULL DEFAULT '{}',
    policy_label TEXT,
    raw_evidence_ref TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cs_msg_user_status
    ON channel_shield_messages(user_id, status);
CREATE INDEX IF NOT EXISTS ix_cs_msg_channel
    ON channel_shield_messages(channel, created_at);

CREATE TABLE IF NOT EXISTS channel_shield_attachments (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    size INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    blob_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cs_att_message
    ON channel_shield_attachments(message_id);

CREATE TABLE IF NOT EXISTS channel_shield_events (
    id TEXT PRIMARY KEY,
    message_id TEXT,
    protection_id TEXT,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cs_evt_message
    ON channel_shield_events(message_id, created_at);
"""


def _data_dir() -> Path:
    raw = (os.environ.get("KEPRIX_DATA_DIR") or "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".keprix" / "data"


def sqlite_path() -> Path:
    override = (os.environ.get("CHANNEL_SHIELD_SQLITE_PATH") or "").strip()
    if override:
        return Path(override)
    return _data_dir() / "channel_shield.db"


def durable_enabled() -> bool:
    mode = (os.environ.get("CHANNEL_SHIELD_STORE") or "").strip().lower()
    if mode in {"memory", "mem", "inmemory"}:
        return False
    return True


def _iso(dt: datetime | str | None) -> str:
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


def _parse_dt(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        from datetime import timezone

        return datetime.now(timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class DurableBackend:
    """Write-through persistence for Channel Shield records."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or sqlite_path()
        self._sqlite_ready = False

    def _conn(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        if not self._sqlite_ready:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
            self._sqlite_ready = True
        return conn

    def _use_postgres(self) -> bool:
        try:
            from keprix.database import get_session_factory

            return get_session_factory() is not None
        except Exception:
            return False

    async def load_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        if self._use_postgres():
            try:
                return await self._load_postgres()
            except Exception:
                logger.exception("Channel Shield Postgres load failed; trying SQLite")
        return await self._load_sqlite()

    async def _load_sqlite(self) -> dict[str, list[dict[str, Any]]]:
        import asyncio

        return await asyncio.to_thread(self._load_sqlite_sync)

    def _load_sqlite_sync(self) -> dict[str, list[dict[str, Any]]]:
        with self._conn() as conn:
            protections = [dict(r) for r in conn.execute("SELECT * FROM channel_shield_protections")]
            messages = [dict(r) for r in conn.execute("SELECT * FROM channel_shield_messages")]
            attachments = [dict(r) for r in conn.execute("SELECT * FROM channel_shield_attachments")]
            events = [dict(r) for r in conn.execute("SELECT * FROM channel_shield_events ORDER BY created_at")]
        for rows, json_cols in (
            (protections, ["config"]),
            (messages, ["to_addrs", "envelope", "report", "scout_ids", "agent_safe_content"]),
            (events, ["payload"]),
        ):
            for row in rows:
                for col in json_cols:
                    raw = row.get(col)
                    if isinstance(raw, str):
                        try:
                            row[col] = json.loads(raw)
                        except Exception:
                            row[col] = {} if col != "to_addrs" and col != "scout_ids" else []
                if "enabled" in row:
                    row["enabled"] = bool(row["enabled"])
                if "verified" in row:
                    row["verified"] = bool(row["verified"])
        return {
            "protections": protections,
            "messages": messages,
            "attachments": attachments,
            "events": events,
        }

    async def _load_postgres(self) -> dict[str, list[dict[str, Any]]]:
        from sqlalchemy import select

        from keprix.database import get_session_factory

        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            protections = (await session.execute(select(ChannelShieldProtectionRow))).scalars().all()
            messages = (await session.execute(select(ChannelShieldMessageRow))).scalars().all()
            attachments = (await session.execute(select(ChannelShieldAttachmentRow))).scalars().all()
            events = (await session.execute(select(ChannelShieldEventRow))).scalars().all()
        return {
            "protections": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "channel": r.channel,
                    "label": r.label,
                    "protection_key": r.protection_key,
                    "config": dict(r.config or {}),
                    "enabled": r.enabled,
                    "verified": r.verified,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
                for r in protections
            ],
            "messages": [
                {
                    "id": r.id,
                    "protection_id": r.protection_id,
                    "user_id": r.user_id,
                    "channel": r.channel,
                    "external_message_id": r.external_message_id,
                    "conversation_id": r.conversation_id or "",
                    "from_addr": r.from_addr or "",
                    "to_addrs": list(r.to_addrs or []),
                    "subject": r.subject or "",
                    "text_preview": r.text_preview or "",
                    "status": r.status,
                    "verdict": r.verdict,
                    "envelope": dict(r.envelope or {}),
                    "report": dict(r.report or {}),
                    "safe_summary": r.safe_summary,
                    "raw_blob_id": r.raw_blob_id,
                    "scout_ids": list(r.scout_ids or []),
                    "agent_safe_content": dict(r.agent_safe_content or {}),
                    "policy_label": r.policy_label,
                    "raw_evidence_ref": r.raw_evidence_ref,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
                for r in messages
            ],
            "attachments": [
                {
                    "id": r.id,
                    "message_id": r.message_id,
                    "filename": r.filename,
                    "content_type": r.content_type or "",
                    "size": r.size,
                    "sha256": r.sha256,
                    "storage_uri": r.storage_uri,
                    "blob_id": r.blob_id,
                    "created_at": r.created_at,
                }
                for r in attachments
            ],
            "events": [
                {
                    "id": r.id,
                    "message_id": r.message_id,
                    "protection_id": r.protection_id,
                    "event_type": r.event_type,
                    "payload": dict(r.payload or {}),
                    "created_at": r.created_at,
                }
                for r in events
            ],
        }

    async def upsert_protection(self, row: dict[str, Any]) -> None:
        if self._use_postgres():
            try:
                await self._upsert_protection_pg(row)
                return
            except Exception:
                logger.exception("Channel Shield Postgres protection upsert failed")
        await self._upsert_protection_sqlite(row)

    async def _upsert_protection_sqlite(self, row: dict[str, Any]) -> None:
        import asyncio

        def _run() -> None:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO channel_shield_protections (
                        id, user_id, channel, label, protection_key, config,
                        enabled, verified, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        user_id=excluded.user_id,
                        channel=excluded.channel,
                        label=excluded.label,
                        protection_key=excluded.protection_key,
                        config=excluded.config,
                        enabled=excluded.enabled,
                        verified=excluded.verified,
                        updated_at=excluded.updated_at
                    """,
                    (
                        row["id"],
                        row["user_id"],
                        row["channel"],
                        row["label"],
                        row["protection_key"],
                        json.dumps(row.get("config") or {}),
                        1 if row.get("enabled", True) else 0,
                        1 if row.get("verified") else 0,
                        _iso(row["created_at"]),
                        _iso(row["updated_at"]),
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def _upsert_protection_pg(self, row: dict[str, Any]) -> None:
        from keprix.database import get_session_factory

        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            existing = await session.get(ChannelShieldProtectionRow, row["id"])
            if existing is None:
                session.add(
                    ChannelShieldProtectionRow(
                        id=row["id"],
                        user_id=row["user_id"],
                        channel=row["channel"],
                        label=row["label"],
                        protection_key=row["protection_key"],
                        config=dict(row.get("config") or {}),
                        enabled=bool(row.get("enabled", True)),
                        verified=bool(row.get("verified")),
                        created_at=_parse_dt(row["created_at"]),
                        updated_at=_parse_dt(row["updated_at"]),
                    )
                )
            else:
                existing.user_id = row["user_id"]
                existing.channel = row["channel"]
                existing.label = row["label"]
                existing.protection_key = row["protection_key"]
                existing.config = dict(row.get("config") or {})
                existing.enabled = bool(row.get("enabled", True))
                existing.verified = bool(row.get("verified"))
                existing.updated_at = _parse_dt(row["updated_at"])
            await session.commit()

    async def delete_protection(self, protection_id: str) -> None:
        if self._use_postgres():
            try:
                from keprix.database import get_session_factory

                factory = get_session_factory()
                assert factory is not None
                async with factory() as session:
                    row = await session.get(ChannelShieldProtectionRow, protection_id)
                    if row is not None:
                        await session.delete(row)
                        await session.commit()
                return
            except Exception:
                logger.exception("Channel Shield Postgres protection delete failed")
        import asyncio

        def _run() -> None:
            with self._conn() as conn:
                conn.execute(
                    "DELETE FROM channel_shield_protections WHERE id = ?", (protection_id,)
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def upsert_message(self, row: dict[str, Any]) -> None:
        if self._use_postgres():
            try:
                await self._upsert_message_pg(row)
                return
            except Exception:
                logger.exception("Channel Shield Postgres message upsert failed")
        await self._upsert_message_sqlite(row)

    async def _upsert_message_sqlite(self, row: dict[str, Any]) -> None:
        import asyncio

        def _run() -> None:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO channel_shield_messages (
                        id, protection_id, user_id, channel, external_message_id,
                        conversation_id, from_addr, to_addrs, subject, text_preview,
                        status, verdict, envelope, report, safe_summary, raw_blob_id,
                        scout_ids, agent_safe_content, policy_label, raw_evidence_ref,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        protection_id=excluded.protection_id,
                        status=excluded.status,
                        verdict=excluded.verdict,
                        envelope=excluded.envelope,
                        report=excluded.report,
                        safe_summary=excluded.safe_summary,
                        text_preview=excluded.text_preview,
                        scout_ids=excluded.scout_ids,
                        agent_safe_content=excluded.agent_safe_content,
                        policy_label=excluded.policy_label,
                        raw_evidence_ref=excluded.raw_evidence_ref,
                        raw_blob_id=excluded.raw_blob_id,
                        updated_at=excluded.updated_at
                    """,
                    (
                        row["id"],
                        row["protection_id"],
                        row["user_id"],
                        row["channel"],
                        row["external_message_id"],
                        row.get("conversation_id") or "",
                        row.get("from_addr") or "",
                        json.dumps(row.get("to_addrs") or []),
                        row.get("subject") or "",
                        row.get("text_preview") or "",
                        row["status"],
                        row.get("verdict"),
                        json.dumps(row.get("envelope") or {}),
                        json.dumps(row.get("report") or {}),
                        row.get("safe_summary"),
                        row.get("raw_blob_id"),
                        json.dumps(row.get("scout_ids") or []),
                        json.dumps(row.get("agent_safe_content") or {}),
                        row.get("policy_label"),
                        row.get("raw_evidence_ref"),
                        _iso(row["created_at"]),
                        _iso(row["updated_at"]),
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def _upsert_message_pg(self, row: dict[str, Any]) -> None:
        from keprix.database import get_session_factory

        factory = get_session_factory()
        assert factory is not None
        async with factory() as session:
            existing = await session.get(ChannelShieldMessageRow, row["id"])
            payload = dict(
                protection_id=row["protection_id"],
                user_id=row["user_id"],
                channel=row["channel"],
                external_message_id=row["external_message_id"],
                conversation_id=row.get("conversation_id") or "",
                from_addr=row.get("from_addr") or "",
                to_addrs=list(row.get("to_addrs") or []),
                subject=row.get("subject") or "",
                text_preview=row.get("text_preview") or "",
                status=row["status"],
                verdict=row.get("verdict"),
                envelope=dict(row.get("envelope") or {}),
                report=dict(row.get("report") or {}),
                safe_summary=row.get("safe_summary"),
                raw_blob_id=row.get("raw_blob_id"),
                scout_ids=list(row.get("scout_ids") or []),
                agent_safe_content=dict(row.get("agent_safe_content") or {}),
                policy_label=row.get("policy_label"),
                raw_evidence_ref=row.get("raw_evidence_ref"),
                created_at=_parse_dt(row["created_at"]),
                updated_at=_parse_dt(row["updated_at"]),
            )
            if existing is None:
                session.add(ChannelShieldMessageRow(id=row["id"], **payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            await session.commit()

    async def upsert_attachment(self, row: dict[str, Any]) -> None:
        if self._use_postgres():
            try:
                from keprix.database import get_session_factory

                factory = get_session_factory()
                assert factory is not None
                async with factory() as session:
                    existing = await session.get(ChannelShieldAttachmentRow, row["id"])
                    payload = dict(
                        message_id=row["message_id"],
                        filename=row["filename"],
                        content_type=row.get("content_type") or "",
                        size=int(row.get("size") or 0),
                        sha256=row["sha256"],
                        storage_uri=row["storage_uri"],
                        blob_id=row.get("blob_id"),
                        created_at=_parse_dt(row["created_at"]),
                    )
                    if existing is None:
                        session.add(ChannelShieldAttachmentRow(id=row["id"], **payload))
                    else:
                        for key, value in payload.items():
                            setattr(existing, key, value)
                    await session.commit()
                return
            except Exception:
                logger.exception("Channel Shield Postgres attachment upsert failed")
        import asyncio

        def _run() -> None:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO channel_shield_attachments (
                        id, message_id, filename, content_type, size, sha256,
                        storage_uri, blob_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        filename=excluded.filename,
                        content_type=excluded.content_type,
                        size=excluded.size,
                        sha256=excluded.sha256,
                        storage_uri=excluded.storage_uri,
                        blob_id=excluded.blob_id
                    """,
                    (
                        row["id"],
                        row["message_id"],
                        row["filename"],
                        row.get("content_type") or "",
                        int(row.get("size") or 0),
                        row["sha256"],
                        row["storage_uri"],
                        row.get("blob_id"),
                        _iso(row["created_at"]),
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def insert_event(self, row: dict[str, Any]) -> None:
        if self._use_postgres():
            try:
                from keprix.database import get_session_factory

                factory = get_session_factory()
                assert factory is not None
                async with factory() as session:
                    session.add(
                        ChannelShieldEventRow(
                            id=row["id"],
                            message_id=row.get("message_id"),
                            protection_id=row.get("protection_id"),
                            event_type=row["event_type"],
                            payload=dict(row.get("payload") or {}),
                            created_at=_parse_dt(row["created_at"]),
                        )
                    )
                    await session.commit()
                return
            except Exception:
                logger.exception("Channel Shield Postgres event insert failed")
        import asyncio

        def _run() -> None:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO channel_shield_events (
                        id, message_id, protection_id, event_type, payload, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row.get("message_id"),
                        row.get("protection_id"),
                        row["event_type"],
                        json.dumps(row.get("payload") or {}),
                        _iso(row["created_at"]),
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_run)

"""Governance configuration, event queue, and policy persistence."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update

from keprix.governance.models import GovernanceConfigRow, GovernanceEventQueueRow, GovernancePolicyRow, ensure_governance_tables
from keprix.database import get_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _governance_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "governance"
    except Exception:
        root = Path.home() / ".keprix" / "governance"
    root.mkdir(parents=True, exist_ok=True)
    return root


class GovernanceStore:
    """PostgreSQL-backed store with JSON file fallback."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._force_file = base_dir is not None
        self._dir = base_dir or _governance_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._dir / "config.json"
        self._events_path = self._dir / "events_queue.jsonl"
        self._policies_path = self._dir / "policies.json"

    def _load_file_config(self) -> dict[str, Any]:
        if self._config_path.exists():
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        else:
            data = {
                "enabled": os.environ.get("KEPRIX_GOVERNANCE_ENABLED", "").lower() == "true",
                "provider_endpoint": os.environ.get("KEPRIX_GOVERNANCE_ENDPOINT", ""),
                "api_key_vault_id": None,
                "instance_id": os.environ.get("KEPRIX_GOVERNANCE_WORKSPACE_ID") or None,
                "enrolled_at": None,
                "last_heartbeat_at": None,
                "last_heartbeat_ok": None,
                "reporting_paused": False,
                "consecutive_failures": 0,
                "vault_user_id": None,
            }
        if data.get("endpoint") and not data.get("provider_endpoint"):
            data["provider_endpoint"] = data["endpoint"]
        if data.get("workspace_id") and not data.get("instance_id"):
            data["instance_id"] = data["workspace_id"]
        return data

    def _save_file_config(self, data: dict[str, Any]) -> None:
        self._config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def get_config(self) -> dict[str, Any]:
        if self._force_file:
            return self._load_file_config()
        factory = get_session_factory()
        if factory is None:
            return self._load_file_config()
        await ensure_governance_tables()
        async with factory() as session:
            result = await session.execute(select(GovernanceConfigRow).limit(1))
            row = result.scalar_one_or_none()
            if row is None:
                return self._load_file_config()
            return {
                "id": row.id,
                "enabled": row.enabled,
                "provider_endpoint": row.provider_endpoint,
                "api_key_vault_id": row.api_key_vault_id,
                "instance_id": row.instance_id,
                "enrolled_at": _iso(row.enrolled_at),
                "last_heartbeat_at": _iso(row.last_heartbeat_at),
                "last_heartbeat_ok": row.last_heartbeat_ok,
                "reporting_paused": row.reporting_paused,
                "consecutive_failures": int(row.consecutive_failures or 0),
                "vault_user_id": row.vault_user_id,
            }

    async def save_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        if self._force_file:
            data = self._load_file_config()
            data.update(patch)
            self._save_file_config(data)
            return data
        factory = get_session_factory()
        if factory is None:
            data = self._load_file_config()
            data.update(patch)
            self._save_file_config(data)
            return data

        await ensure_governance_tables()
        async with factory() as session:
            result = await session.execute(select(GovernanceConfigRow).limit(1))
            row = result.scalar_one_or_none()
            if row is None:
                row = GovernanceConfigRow(id=str(uuid.uuid4()))
                session.add(row)
            for key in (
                "enabled",
                "provider_endpoint",
                "api_key_vault_id",
                "instance_id",
                "enrolled_at",
                "last_heartbeat_at",
                "last_heartbeat_ok",
                "reporting_paused",
                "consecutive_failures",
                "vault_user_id",
            ):
                if key not in patch:
                    continue
                value = patch[key]
                if key.endswith("_at") and isinstance(value, str):
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                setattr(row, key, value)
            await session.commit()
            await session.refresh(row)
            return {
                "id": row.id,
                "enabled": row.enabled,
                "provider_endpoint": row.provider_endpoint,
                "api_key_vault_id": row.api_key_vault_id,
                "instance_id": row.instance_id,
                "enrolled_at": _iso(row.enrolled_at),
                "last_heartbeat_at": _iso(row.last_heartbeat_at),
                "last_heartbeat_ok": row.last_heartbeat_ok,
                "reporting_paused": row.reporting_paused,
                "consecutive_failures": int(row.consecutive_failures or 0),
                "vault_user_id": row.vault_user_id,
            }

    async def enqueue_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        factory = get_session_factory()
        row_data = {
            "event_type": event_type,
            "payload": payload,
            "created_at": _utcnow().isoformat(),
            "sent": False,
        }
        if self._force_file or factory is None:
            row_data["id"] = str(uuid.uuid4())
            with self._events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row_data) + "\n")
            return row_data

        await ensure_governance_tables()
        async with factory() as session:
            row = GovernanceEventQueueRow(event_type=event_type, payload=payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return {
                "id": row.id,
                "event_type": row.event_type,
                "payload": row.payload,
                "sent": row.sent,
                "created_at": _iso(row.created_at),
            }

    async def list_pending_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if self._force_file or factory is None:
            if not self._events_path.exists():
                return []
            pending = []
            for line in self._events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if not row.get("sent"):
                    pending.append(row)
            return pending[:limit]

        await ensure_governance_tables()
        async with factory() as session:
            result = await session.execute(
                select(GovernanceEventQueueRow)
                .where(GovernanceEventQueueRow.sent.is_(False))
                .order_by(GovernanceEventQueueRow.id.asc())
                .limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "payload": row.payload,
                    "sent": row.sent,
                    "created_at": _iso(row.created_at),
                }
                for row in rows
            ]

    async def mark_events_sent(self, event_ids: list[int | str]) -> None:
        factory = get_session_factory()
        if self._force_file or factory is None:
            if not self._events_path.exists():
                return
            lines = []
            id_set = {str(item) for item in event_ids}
            for line in self._events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if str(row.get("id")) in id_set:
                    row["sent"] = True
                    row["sent_at"] = _utcnow().isoformat()
                lines.append(json.dumps(row))
            self._events_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            return

        await ensure_governance_tables()
        int_ids = [int(item) for item in event_ids]
        async with factory() as session:
            await session.execute(
                update(GovernanceEventQueueRow)
                .where(GovernanceEventQueueRow.id.in_(int_ids))
                .values(sent=True, sent_at=_utcnow())
            )
            await session.commit()

    async def list_recent_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if self._force_file or factory is None:
            if not self._events_path.exists():
                return []
            rows = [json.loads(line) for line in self._events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            return list(reversed(rows[-limit:]))

        await ensure_governance_tables()
        async with factory() as session:
            result = await session.execute(
                select(GovernanceEventQueueRow).order_by(GovernanceEventQueueRow.id.desc()).limit(limit)
            )
            return [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "payload": row.payload,
                    "sent": row.sent,
                    "sent_at": _iso(row.sent_at),
                    "created_at": _iso(row.created_at),
                }
                for row in result.scalars().all()
            ]

    async def add_policy(self, policy_type: str, policy_value: dict[str, Any]) -> dict[str, Any]:
        factory = get_session_factory()
        row_data = {
            "id": str(uuid.uuid4()),
            "policy_type": policy_type,
            "policy_value": policy_value,
            "received_at": _utcnow().isoformat(),
            "active": True,
        }
        if self._force_file or factory is None:
            policies = []
            if self._policies_path.exists():
                policies = json.loads(self._policies_path.read_text(encoding="utf-8"))
            policies.append(row_data)
            self._policies_path.write_text(json.dumps(policies, indent=2), encoding="utf-8")
            return row_data

        await ensure_governance_tables()
        async with factory() as session:
            row = GovernancePolicyRow(
                id=row_data["id"],
                policy_type=policy_type,
                policy_value=policy_value,
            )
            session.add(row)
            await session.commit()
            return row_data

    async def list_policies(self, *, active_only: bool = True) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if self._force_file or factory is None:
            if not self._policies_path.exists():
                return []
            policies = json.loads(self._policies_path.read_text(encoding="utf-8"))
            if active_only:
                policies = [row for row in policies if row.get("active", True)]
            return policies

        await ensure_governance_tables()
        async with factory() as session:
            query = select(GovernancePolicyRow).order_by(GovernancePolicyRow.received_at.desc())
            if active_only:
                query = query.where(GovernancePolicyRow.active.is_(True))
            result = await session.execute(query)
            return [
                {
                    "id": row.id,
                    "policy_type": row.policy_type,
                    "policy_value": row.policy_value,
                    "received_at": _iso(row.received_at),
                    "active": row.active,
                }
                for row in result.scalars().all()
            ]


_store: GovernanceStore | None = None


def get_governance_store() -> GovernanceStore:
    global _store
    if _store is None:
        _store = GovernanceStore()
    return _store

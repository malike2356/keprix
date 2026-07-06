"""Pack gate persistence (PostgreSQL with JSON file fallback)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from keprix.pack_gate.models import (
    PackGateConfigRow,
    PackGateRecordRow,
    PackGateRollbackLogRow,
    ensure_pack_gate_tables,
)
from keprix.database import get_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _gate_dir() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        root = Path(env) / "pack_gate"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "pack_gate"
        except Exception:
            root = Path.home() / ".keprix" / "pack_gate"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _record_to_dict(row: PackGateRecordRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "pack_id": row.pack_id,
        "from_version": row.from_version,
        "to_version": row.to_version,
        "changelog_text": row.changelog_text,
        "status": row.status,
        "signed_off_by_user_id": row.signed_off_by_user_id,
        "signed_off_at": _iso(row.signed_off_at),
        "sign_off_note": row.sign_off_note,
        "requested_at": _iso(row.requested_at) or _iso(_utcnow()),
        "requested_by_user_id": row.requested_by_user_id,
    }


class PackGateStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _gate_dir()

    def _config_path(self, workspace_id: str) -> Path:
        return self._dir / f"config_{workspace_id}.json"

    def _records_path(self, workspace_id: str) -> Path:
        return self._dir / f"records_{workspace_id}.json"

    def _rollback_path(self, workspace_id: str) -> Path:
        return self._dir / f"rollback_{workspace_id}.jsonl"

    def _load_file_config(self, workspace_id: str) -> dict[str, Any]:
        path = self._config_path(workspace_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {
            "workspace_id": workspace_id,
            "enabled": False,
            "approver_user_id": None,
            "approver_email": None,
            "notify_on_install": True,
            "require_changelog": True,
            "updated_at": _iso(_utcnow()),
        }

    def _save_file_config(self, workspace_id: str, data: dict[str, Any]) -> None:
        data["workspace_id"] = workspace_id
        data["updated_at"] = _iso(_utcnow())
        path = self._config_path(workspace_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_file_records(self, workspace_id: str) -> list[dict[str, Any]]:
        path = self._records_path(workspace_id)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_file_records(self, workspace_id: str, rows: list[dict[str, Any]]) -> None:
        path = self._records_path(workspace_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    async def get_config(self, workspace_id: str) -> dict[str, Any]:
        factory = get_session_factory()
        if factory is None:
            return self._load_file_config(workspace_id)
        await ensure_pack_gate_tables()
        async with factory() as session:
            result = await session.execute(
                select(PackGateConfigRow).where(PackGateConfigRow.workspace_id == workspace_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return self._load_file_config(workspace_id)
            return {
                "workspace_id": row.workspace_id,
                "enabled": row.enabled,
                "approver_user_id": row.approver_user_id,
                "approver_email": row.approver_email,
                "notify_on_install": row.notify_on_install,
                "require_changelog": row.require_changelog,
                "updated_at": _iso(row.updated_at),
            }

    async def save_config(self, workspace_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        factory = get_session_factory()
        if factory is None:
            current = self._load_file_config(workspace_id)
            current.update(patch)
            self._save_file_config(workspace_id, current)
            return current
        await ensure_pack_gate_tables()
        async with factory() as session:
            result = await session.execute(
                select(PackGateConfigRow).where(PackGateConfigRow.workspace_id == workspace_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = PackGateConfigRow(workspace_id=workspace_id)
                session.add(row)
            for key, value in patch.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = _utcnow()
            await session.commit()
            await session.refresh(row)
            return {
                "workspace_id": row.workspace_id,
                "enabled": row.enabled,
                "approver_user_id": row.approver_user_id,
                "approver_email": row.approver_email,
                "notify_on_install": row.notify_on_install,
                "require_changelog": row.require_changelog,
                "updated_at": _iso(row.updated_at),
            }

    async def create_record(
        self,
        *,
        workspace_id: str,
        pack_id: str,
        to_version: str,
        from_version: str | None,
        changelog_text: str | None,
        requested_by_user_id: str | None,
    ) -> dict[str, Any]:
        record_id = str(uuid.uuid4())
        now = _utcnow()
        payload = {
            "id": record_id,
            "workspace_id": workspace_id,
            "pack_id": pack_id,
            "from_version": from_version,
            "to_version": to_version,
            "changelog_text": changelog_text,
            "status": "pending",
            "signed_off_by_user_id": None,
            "signed_off_at": None,
            "sign_off_note": None,
            "requested_at": _iso(now),
            "requested_by_user_id": requested_by_user_id,
        }
        factory = get_session_factory()
        if factory is None:
            rows = self._load_file_records(workspace_id)
            for row in rows:
                if row["pack_id"] == pack_id and row["to_version"] == to_version:
                    return row
            rows.append(payload)
            self._save_file_records(workspace_id, rows)
            return payload
        await ensure_pack_gate_tables()
        async with factory() as session:
            existing = await session.execute(
                select(PackGateRecordRow).where(
                    PackGateRecordRow.workspace_id == workspace_id,
                    PackGateRecordRow.pack_id == pack_id,
                    PackGateRecordRow.to_version == to_version,
                )
            )
            row = existing.scalar_one_or_none()
            if row is not None:
                return _record_to_dict(row)
            row = PackGateRecordRow(
                id=record_id,
                workspace_id=workspace_id,
                pack_id=pack_id,
                from_version=from_version,
                to_version=to_version,
                changelog_text=changelog_text,
                status="pending",
                requested_at=now,
                requested_by_user_id=requested_by_user_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _record_to_dict(row)

    async def get_record(self, workspace_id: str, record_id: str) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            for row in self._load_file_records(workspace_id):
                if row["id"] == record_id:
                    return row
            return None
        await ensure_pack_gate_tables()
        async with factory() as session:
            result = await session.execute(
                select(PackGateRecordRow).where(
                    PackGateRecordRow.workspace_id == workspace_id,
                    PackGateRecordRow.id == record_id,
                )
            )
            row = result.scalar_one_or_none()
            return _record_to_dict(row) if row else None

    async def get_record_for_version(
        self, workspace_id: str, pack_id: str, to_version: str
    ) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            for row in self._load_file_records(workspace_id):
                if row["pack_id"] == pack_id and row["to_version"] == to_version:
                    return row
            return None
        await ensure_pack_gate_tables()
        async with factory() as session:
            result = await session.execute(
                select(PackGateRecordRow).where(
                    PackGateRecordRow.workspace_id == workspace_id,
                    PackGateRecordRow.pack_id == pack_id,
                    PackGateRecordRow.to_version == to_version,
                )
            )
            row = result.scalar_one_or_none()
            return _record_to_dict(row) if row else None

    async def list_records(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        pack_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        factory = get_session_factory()
        if factory is None:
            rows = self._load_file_records(workspace_id)
            if status:
                rows = [row for row in rows if row.get("status") == status]
            if pack_id:
                rows = [row for row in rows if row.get("pack_id") == pack_id]
            rows.sort(key=lambda row: row.get("requested_at") or "", reverse=True)
            total = len(rows)
            return rows[offset : offset + limit], total
        await ensure_pack_gate_tables()
        async with factory() as session:
            query = select(PackGateRecordRow).where(PackGateRecordRow.workspace_id == workspace_id)
            if status:
                query = query.where(PackGateRecordRow.status == status)
            if pack_id:
                query = query.where(PackGateRecordRow.pack_id == pack_id)
            result = await session.execute(query)
            all_rows = [_record_to_dict(row) for row in result.scalars().all()]
            all_rows.sort(key=lambda row: row.get("requested_at") or "", reverse=True)
            total = len(all_rows)
            return all_rows[offset : offset + limit], total

    async def update_record_status(
        self,
        workspace_id: str,
        record_id: str,
        *,
        status: str,
        signed_off_by_user_id: str | None,
        sign_off_note: str | None,
    ) -> dict[str, Any] | None:
        now = _utcnow()
        factory = get_session_factory()
        if factory is None:
            rows = self._load_file_records(workspace_id)
            for row in rows:
                if row["id"] == record_id:
                    row["status"] = status
                    row["signed_off_by_user_id"] = signed_off_by_user_id
                    row["signed_off_at"] = _iso(now)
                    row["sign_off_note"] = sign_off_note
                    self._save_file_records(workspace_id, rows)
                    return row
            return None
        await ensure_pack_gate_tables()
        async with factory() as session:
            result = await session.execute(
                select(PackGateRecordRow).where(
                    PackGateRecordRow.workspace_id == workspace_id,
                    PackGateRecordRow.id == record_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            row.status = status
            row.signed_off_by_user_id = signed_off_by_user_id
            row.signed_off_at = now
            row.sign_off_note = sign_off_note
            await session.commit()
            await session.refresh(row)
            return _record_to_dict(row)

    async def last_approved_version(self, workspace_id: str, pack_id: str, before_version: str | None = None) -> str | None:
        records, _ = await self.list_records(workspace_id, pack_id=pack_id, status="approved", limit=500)
        for row in records:
            version = row.get("to_version")
            if before_version and version == before_version:
                continue
            return str(version) if version else None
        return None

    async def append_rollback_log(
        self,
        *,
        workspace_id: str,
        pack_id: str,
        rolled_back_from_version: str,
        rolled_back_to_version: str,
        reason: str | None,
        initiated_by_user_id: str | None,
        gate_record_id: str | None,
    ) -> dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "pack_id": pack_id,
            "rolled_back_from_version": rolled_back_from_version,
            "rolled_back_to_version": rolled_back_to_version,
            "reason": reason,
            "initiated_by_user_id": initiated_by_user_id,
            "initiated_at": _iso(_utcnow()),
            "gate_record_id": gate_record_id,
        }
        factory = get_session_factory()
        if factory is None:
            path = self._rollback_path(workspace_id)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
            return entry
        await ensure_pack_gate_tables()
        async with factory() as session:
            row = PackGateRollbackLogRow(
                id=entry["id"],
                workspace_id=workspace_id,
                pack_id=pack_id,
                rolled_back_from_version=rolled_back_from_version,
                rolled_back_to_version=rolled_back_to_version,
                reason=reason,
                initiated_by_user_id=initiated_by_user_id,
                gate_record_id=gate_record_id,
            )
            session.add(row)
            await session.commit()
            return entry


_store: PackGateStore | None = None


def get_pack_gate_store(base_dir: Path | None = None) -> PackGateStore:
    global _store
    if base_dir is not None:
        return PackGateStore(base_dir=base_dir)
    if _store is None:
        _store = PackGateStore()
    return _store


def reset_pack_gate_store() -> None:
    global _store
    _store = None

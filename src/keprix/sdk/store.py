"""Persistence for registered SDK apps and action plans."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from keprix.sdk.schemas import ActionPlanModel, DomainSchema, RegisterAppRequest


def _sdk_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home()) / "sdk"
    except Exception:
        return Path.home() / ".keprix" / "sdk"


class SdkStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or _sdk_dir()
        self._apps_path = self._base / "apps.json"
        self._plans_path = self._base / "plans.json"

    def _read_apps(self) -> list[dict[str, Any]]:
        if not self._apps_path.exists():
            return []
        return json.loads(self._apps_path.read_text(encoding="utf-8"))

    def _write_apps(self, rows: list[dict[str, Any]]) -> None:
        self._base.mkdir(parents=True, exist_ok=True)
        self._apps_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def _read_plans(self) -> list[dict[str, Any]]:
        if not self._plans_path.exists():
            return []
        return json.loads(self._plans_path.read_text(encoding="utf-8"))

    def _write_plans(self, rows: list[dict[str, Any]]) -> None:
        self._base.mkdir(parents=True, exist_ok=True)
        self._plans_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def register_app(self, body: RegisterAppRequest, api_token_id: str | None = None) -> dict[str, Any]:
        rows = self._read_apps()
        for row in rows:
            if row["name"] == body.name and row.get("is_active", True):
                row.update(
                    {
                        "version": body.version,
                        "domain_schema": body.domain.model_dump(),
                        "webhook_url": body.webhook_url,
                        "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                self._write_apps(rows)
                return row
        app_id = str(uuid.uuid4())
        row = {
            "id": app_id,
            "name": body.name,
            "version": body.version,
            "domain_schema": body.domain.model_dump(),
            "webhook_url": body.webhook_url,
            "api_token_id": api_token_id,
            "is_active": True,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }
        rows.append(row)
        self._write_apps(rows)
        return row

    def list_apps(self) -> list[dict[str, Any]]:
        return [row for row in self._read_apps() if row.get("is_active", True)]

    def get_app(self, app_id: str) -> dict[str, Any] | None:
        for row in self._read_apps():
            if row["id"] == app_id and row.get("is_active", True):
                return row
        return None

    def get_app_by_name(self, name: str) -> dict[str, Any] | None:
        for row in self._read_apps():
            if row["name"] == name and row.get("is_active", True):
                return row
        return None

    def unregister_app(self, app_id: str) -> bool:
        rows = self._read_apps()
        updated = False
        for row in rows:
            if row["id"] == app_id:
                row["is_active"] = False
                updated = True
        if updated:
            self._write_apps(rows)
        return updated

    def update_schema(self, app_id: str, domain: DomainSchema) -> dict[str, Any] | None:
        rows = self._read_apps()
        for row in rows:
            if row["id"] == app_id and row.get("is_active", True):
                row["domain_schema"] = domain.model_dump()
                row["last_seen_at"] = datetime.now(timezone.utc).isoformat()
                self._write_apps(rows)
                return row
        return None

    def touch_app(self, app_id: str) -> None:
        rows = self._read_apps()
        for row in rows:
            if row["id"] == app_id:
                row["last_seen_at"] = datetime.now(timezone.utc).isoformat()
        self._write_apps(rows)

    def save_plan(self, app_id: str, plan: ActionPlanModel, *, status: str) -> dict[str, Any]:
        plan_id = plan.plan_id or str(uuid.uuid4())
        plan.plan_id = plan_id
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        row = {
            "id": plan_id,
            "app_id": app_id,
            "user_input": plan.user_input,
            "session_id": plan.session_id,
            "plan": plan.model_dump(),
            "status": status,
            "requires_confirmation": plan.requires_confirmation,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
            "delivered_at": None,
            "delivery_response": None,
        }
        rows = self._read_plans()
        rows.append(row)
        self._write_plans(rows)
        return row

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        for row in self._read_plans():
            if row["id"] == plan_id:
                return row
        return None

    def update_plan(self, plan_id: str, **fields: Any) -> dict[str, Any] | None:
        rows = self._read_plans()
        for row in rows:
            if row["id"] == plan_id:
                row.update(fields)
                self._write_plans(rows)
                return row
        return None

    def list_plans(self, app_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = [row for row in self._read_plans() if row["app_id"] == app_id]
        return list(reversed(rows[-limit:]))


_store: SdkStore | None = None


def get_sdk_store() -> SdkStore:
    global _store
    if _store is None:
        _store = SdkStore()
    return _store

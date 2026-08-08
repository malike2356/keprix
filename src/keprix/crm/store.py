"""SQLite-backed CRM store with workspace isolation (Soft Wall pattern)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from keprix.crm.models import (
    ALL_STAGES,
    DEFAULT_DOMAIN_PACK,
    ContactabilityVerdict,
    CrmStage,
    MergeSuggestionStatus,
    OutboxStatus,
    ProvenanceKind,
)
from keprix.crm.schema import SQLITE_SCHEMA

JSON_LIST_FIELDS = frozenset(
    {"emails", "phones", "tags", "telegram_ids", "addresses", "match_keys"}
)
JSON_DICT_FIELDS = frozenset(
    {
        "scores",
        "metadata",
        "proposal_json",
        "params_json",
        "result_counts_json",
        "checkpoint_json",
        "payload_json",
        "result_json",
        "snapshot_json",
        "field_diff_json",
        "value_json",
    }
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data_root() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "crm"
    except Exception:
        root = Path.home() / ".keprix" / "crm"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, default=str)


def _dumps_list(value: Any) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return json.dumps(parsed)
        except json.JSONDecodeError:
            return json.dumps([value])
        return json.dumps([value])
    return json.dumps(list(value))


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key, val in list(data.items()):
        if key in JSON_LIST_FIELDS and isinstance(val, str):
            try:
                data[key] = json.loads(val or "[]")
            except json.JSONDecodeError:
                data[key] = []
        elif key in JSON_DICT_FIELDS and isinstance(val, str):
            try:
                data[key] = json.loads(val or "{}")
            except json.JSONDecodeError:
                data[key] = {}
        elif key in (
            "verified",
            "spf_ok",
            "dkim_ok",
            "dmarc_ok",
            "enabled",
            "reversible",
        ) and val is not None:
            data[key] = bool(val)
    # Normalize stored JSON column names to cleaner API keys where helpful.
    if "proposal_json" in data:
        data["proposal"] = data.pop("proposal_json")
    if "params_json" in data:
        data["params"] = data.pop("params_json")
    if "result_counts_json" in data:
        data["result_counts"] = data.pop("result_counts_json")
    if "checkpoint_json" in data:
        data["checkpoint"] = data.pop("checkpoint_json")
    if "payload_json" in data:
        data["payload"] = data.pop("payload_json")
    if "result_json" in data:
        data["result"] = data.pop("result_json")
    if "snapshot_json" in data:
        data["snapshot"] = data.pop("snapshot_json")
    if "field_diff_json" in data:
        data["field_diff"] = data.pop("field_diff_json")
    if "value_json" in data:
        data["value"] = data.pop("value_json")
    return data


def _normalise_email(value: str | None) -> str | None:
    if not value:
        return None
    return str(value).strip().lower() or None


def _emails_from_fields(fields: dict[str, Any]) -> list[Any]:
    emails = fields.get("emails")
    if emails is None and fields.get("email"):
        return [{"address": _normalise_email(str(fields["email"])), "primary": True}]
    if isinstance(emails, str):
        return [{"address": _normalise_email(emails), "primary": True}]
    return list(emails or [])


def _primary_email(emails: list[Any]) -> str | None:
    for item in emails:
        if isinstance(item, dict):
            addr = _normalise_email(item.get("address") or item.get("email"))
            if addr:
                return addr
        elif isinstance(item, str):
            addr = _normalise_email(item)
            if addr:
                return addr
    return None


class CrmStore:
    """Central workspace-scoped CRM repository. Callers must pass workspace_id."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (_data_root() / "crm.sqlite")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SQLITE_SCHEMA)
        self._conn.commit()
        try:
            from keprix.crm.nice_schema import ensure_nice_schema

            ensure_nice_schema(self)
        except Exception:
            pass

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        cur = self._conn.execute(sql, params)
        return _row_to_dict(cur.fetchone())

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        cur = self._conn.execute(sql, params)
        return [d for r in cur.fetchall() if (d := _row_to_dict(r))]

    def _require_workspace(self, workspace_id: str) -> str:
        ws = str(workspace_id or "").strip()
        if not ws:
            raise ValueError("workspace_id is required")
        return ws

    def _get(
        self,
        table: str,
        workspace_id: str,
        row_id: str,
        *,
        include_deleted: bool = False,
    ) -> dict[str, Any] | None:
        ws = self._require_workspace(workspace_id)
        sql = f"SELECT * FROM {table} WHERE id = ? AND workspace_id = ?"
        if not include_deleted and "deleted_at" in self._columns(table):
            sql += " AND deleted_at IS NULL"
        return self._fetchone(sql, (row_id, ws))

    def _columns(self, table: str) -> set[str]:
        cur = self._conn.execute(f"PRAGMA table_info({table})")
        return {str(r[1]) for r in cur.fetchall()}

    def _list(
        self,
        table: str,
        workspace_id: str,
        *,
        include_deleted: bool = False,
        order_by: str = "created_at DESC",
        limit: int = 200,
        offset: int = 0,
        where: str = "",
        params: tuple = (),
    ) -> list[dict[str, Any]]:
        ws = self._require_workspace(workspace_id)
        clauses = ["workspace_id = ?"]
        values: list[Any] = [ws]
        if not include_deleted and "deleted_at" in self._columns(table):
            clauses.append("deleted_at IS NULL")
        if where:
            clauses.append(f"({where})")
            values.extend(params)
        sql = (
            f"SELECT * FROM {table} WHERE {' AND '.join(clauses)} "
            f"ORDER BY {order_by} LIMIT ? OFFSET ?"
        )
        values.extend([int(limit), int(offset)])
        return self._fetchall(sql, tuple(values))

    def _soft_delete(self, table: str, workspace_id: str, row_id: str) -> dict[str, Any] | None:
        ws = self._require_workspace(workspace_id)
        now = _utcnow()
        with self._lock:
            cols = self._columns(table)
            if "deleted_at" not in cols:
                self._conn.execute(
                    f"DELETE FROM {table} WHERE id = ? AND workspace_id = ?",
                    (row_id, ws),
                )
                self._conn.commit()
                return None
            sets = ["deleted_at = ?"]
            vals: list[Any] = [now]
            if "updated_at" in cols:
                sets.append("updated_at = ?")
                vals.append(now)
            if "version" in cols:
                sets.append("version = version + 1")
            vals.extend([row_id, ws])
            self._conn.execute(
                f"UPDATE {table} SET {', '.join(sets)} WHERE id = ? AND workspace_id = ? "
                f"AND deleted_at IS NULL",
                tuple(vals),
            )
            self._conn.commit()
        return self._get(table, ws, row_id, include_deleted=True)

    def _bump_update(
        self,
        table: str,
        workspace_id: str,
        row_id: str,
        updates: dict[str, Any],
        *,
        expected_version: int | None = None,
        allowed: Iterable[str],
    ) -> dict[str, Any] | None:
        ws = self._require_workspace(workspace_id)
        existing = self._get(table, ws, row_id)
        if not existing:
            return None
        if expected_version is not None and int(existing.get("version") or 0) != int(expected_version):
            raise ConflictError(
                f"{table} version mismatch: expected {expected_version}, "
                f"got {existing.get('version')}"
            )
        clean: dict[str, Any] = {}
        allowed_set = set(allowed)
        for key, value in updates.items():
            if key not in allowed_set or value is None:
                continue
            if key == "stage" and str(value) not in ALL_STAGES:
                raise ValueError(f"invalid stage: {value}")
            if key in JSON_LIST_FIELDS:
                clean[key] = _dumps_list(value)
            elif key in JSON_DICT_FIELDS or key in (
                "proposal",
                "params",
                "result_counts",
                "checkpoint",
                "payload",
                "result",
                "snapshot",
                "field_diff",
                "value",
            ):
                col = {
                    "proposal": "proposal_json",
                    "params": "params_json",
                    "result_counts": "result_counts_json",
                    "checkpoint": "checkpoint_json",
                    "payload": "payload_json",
                    "result": "result_json",
                    "snapshot": "snapshot_json",
                    "field_diff": "field_diff_json",
                    "value": "value_json",
                }.get(key, key)
                clean[col] = _dumps(value)
            elif key in ("verified", "spf_ok", "dkim_ok", "dmarc_ok", "enabled", "reversible"):
                clean[key] = 1 if value else 0
            else:
                clean[key] = value
        if not clean:
            return existing
        clean["updated_at"] = _utcnow()
        cols = self._columns(table)
        if "version" in cols:
            set_sql = ", ".join([*(f"{k} = ?" for k in clean), "version = version + 1"])
        else:
            set_sql = ", ".join(f"{k} = ?" for k in clean)
        with self._lock:
            self._conn.execute(
                f"UPDATE {table} SET {set_sql} WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL",
                (*clean.values(), row_id, ws),
            )
            self._conn.commit()
        return self._get(table, ws, row_id)

    # ── Accounts ──────────────────────────────────────────────
    def create_account(self, workspace_id: str, name: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_accounts",
            workspace_id,
            {
                "name": name,
                "company_number": fields.get("company_number"),
                "domain": (str(fields["domain"]).strip().lower() if fields.get("domain") else None),
                "emails": _emails_from_fields(fields),
                "phones": list(fields.get("phones") or []),
                "source": fields.get("source"),
                "domain_pack": fields.get("domain_pack") or DEFAULT_DOMAIN_PACK,
                "stage": fields.get("stage") or CrmStage.DISCOVERED,
                "scores": fields.get("scores") or {},
                "tags": list(fields.get("tags") or []),
                "assigned_agent": fields.get("assigned_agent"),
                "last_touch_at": fields.get("last_touch_at"),
                "external_source_id": fields.get("external_source_id"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def get_account(self, workspace_id: str, account_id: str) -> dict[str, Any] | None:
        return self._get("crm_accounts", workspace_id, account_id)

    def list_accounts(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_accounts", workspace_id, **kwargs)

    def update_account(
        self,
        workspace_id: str,
        account_id: str,
        *,
        expected_version: int | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_accounts",
            workspace_id,
            account_id,
            fields,
            expected_version=expected_version,
            allowed={
                "name",
                "company_number",
                "domain",
                "emails",
                "phones",
                "source",
                "domain_pack",
                "stage",
                "scores",
                "tags",
                "assigned_agent",
                "last_touch_at",
                "external_source_id",
                "actor_type",
                "actor_id",
            },
        )

    def delete_account(self, workspace_id: str, account_id: str) -> dict[str, Any] | None:
        return self._soft_delete("crm_accounts", workspace_id, account_id)

    def upsert_account(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        existing = self._find_account_key(ws, fields)
        if existing:
            updated = self.update_account(ws, existing["id"], **fields)
            return updated or existing
        name = str(fields.pop("name", None) or fields.get("company_name") or "Untitled account")
        return self.create_account(ws, name, **fields)

    def _find_account_key(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        ext = fields.get("external_source_id")
        if ext:
            row = self._fetchone(
                "SELECT * FROM crm_accounts WHERE workspace_id = ? AND external_source_id = ? "
                "AND deleted_at IS NULL",
                (workspace_id, str(ext)),
            )
            if row:
                return row
        ch = fields.get("company_number")
        if ch:
            row = self._fetchone(
                "SELECT * FROM crm_accounts WHERE workspace_id = ? AND company_number = ? "
                "AND deleted_at IS NULL",
                (workspace_id, str(ch).strip()),
            )
            if row:
                return row
        domain = fields.get("domain")
        if domain:
            row = self._fetchone(
                "SELECT * FROM crm_accounts WHERE workspace_id = ? AND lower(domain) = ? "
                "AND deleted_at IS NULL",
                (workspace_id, str(domain).strip().lower()),
            )
            if row:
                return row
        email = _primary_email(_emails_from_fields(fields))
        if email:
            for row in self.list_accounts(workspace_id, limit=500):
                if _primary_email(row.get("emails") or []) == email:
                    return row
        return None

    # ── Leads ─────────────────────────────────────────────────
    def create_lead(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_leads",
            workspace_id,
            {
                "account_id": fields.get("account_id"),
                "name": fields.get("name"),
                "company_name": fields.get("company_name"),
                "company_number": fields.get("company_number"),
                "emails": _emails_from_fields(fields),
                "phones": list(fields.get("phones") or []),
                "source": fields.get("source"),
                "domain_pack": fields.get("domain_pack") or DEFAULT_DOMAIN_PACK,
                "stage": fields.get("stage") or CrmStage.DISCOVERED,
                "scores": fields.get("scores") or {},
                "tags": list(fields.get("tags") or []),
                "assigned_agent": fields.get("assigned_agent"),
                "last_touch_at": fields.get("last_touch_at"),
                "external_source_id": fields.get("external_source_id"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def get_lead(self, workspace_id: str, lead_id: str) -> dict[str, Any] | None:
        return self._get("crm_leads", workspace_id, lead_id)

    def list_leads(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_leads", workspace_id, **kwargs)

    def update_lead(
        self,
        workspace_id: str,
        lead_id: str,
        *,
        expected_version: int | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_leads",
            workspace_id,
            lead_id,
            fields,
            expected_version=expected_version,
            allowed={
                "account_id",
                "name",
                "company_name",
                "company_number",
                "emails",
                "phones",
                "source",
                "domain_pack",
                "stage",
                "scores",
                "tags",
                "assigned_agent",
                "last_touch_at",
                "external_source_id",
                "actor_type",
                "actor_id",
            },
        )

    def delete_lead(self, workspace_id: str, lead_id: str) -> dict[str, Any] | None:
        return self._soft_delete("crm_leads", workspace_id, lead_id)

    def upsert_lead(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        existing = self._find_lead_key(ws, fields)
        if existing:
            return self.update_lead(ws, existing["id"], **fields) or existing
        return self.create_lead(ws, **fields)

    def _find_lead_key(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        ext = fields.get("external_source_id")
        if ext:
            row = self._fetchone(
                "SELECT * FROM crm_leads WHERE workspace_id = ? AND external_source_id = ? "
                "AND deleted_at IS NULL",
                (workspace_id, str(ext)),
            )
            if row:
                return row
        ch = fields.get("company_number")
        if ch:
            row = self._fetchone(
                "SELECT * FROM crm_leads WHERE workspace_id = ? AND company_number = ? "
                "AND deleted_at IS NULL",
                (workspace_id, str(ch).strip()),
            )
            if row:
                return row
        email = _primary_email(_emails_from_fields(fields))
        if email:
            for row in self.list_leads(workspace_id, limit=500):
                if _primary_email(row.get("emails") or []) == email:
                    return row
        return None

    # ── Contacts ──────────────────────────────────────────────
    def create_contact(self, workspace_id: str, display_name: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_contacts",
            workspace_id,
            {
                "account_id": fields.get("account_id"),
                "display_name": display_name,
                "given_name": fields.get("given_name"),
                "family_name": fields.get("family_name"),
                "emails": _emails_from_fields(fields),
                "phones": list(fields.get("phones") or []),
                "telegram_ids": list(fields.get("telegram_ids") or []),
                "addresses": list(fields.get("addresses") or []),
                "source": fields.get("source"),
                "domain_pack": fields.get("domain_pack") or DEFAULT_DOMAIN_PACK,
                "stage": fields.get("stage") or CrmStage.DISCOVERED,
                "scores": fields.get("scores") or {},
                "tags": list(fields.get("tags") or []),
                "assigned_agent": fields.get("assigned_agent"),
                "last_touch_at": fields.get("last_touch_at"),
                "external_source_id": fields.get("external_source_id"),
                "contacts_module_id": fields.get("contacts_module_id"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def get_contact(self, workspace_id: str, contact_id: str) -> dict[str, Any] | None:
        return self._get("crm_contacts", workspace_id, contact_id)

    def list_contacts(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_contacts", workspace_id, **kwargs)

    def update_contact(
        self,
        workspace_id: str,
        contact_id: str,
        *,
        expected_version: int | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_contacts",
            workspace_id,
            contact_id,
            fields,
            expected_version=expected_version,
            allowed={
                "account_id",
                "display_name",
                "given_name",
                "family_name",
                "emails",
                "phones",
                "telegram_ids",
                "addresses",
                "source",
                "domain_pack",
                "stage",
                "scores",
                "tags",
                "assigned_agent",
                "last_touch_at",
                "external_source_id",
                "contacts_module_id",
                "actor_type",
                "actor_id",
            },
        )

    def delete_contact(self, workspace_id: str, contact_id: str) -> dict[str, Any] | None:
        return self._soft_delete("crm_contacts", workspace_id, contact_id)

    def upsert_contact(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        existing = self._find_contact_key(ws, fields)
        if existing:
            return self.update_contact(ws, existing["id"], **fields) or existing
        name = str(
            fields.pop("display_name", None)
            or fields.pop("name", None)
            or _primary_email(_emails_from_fields(fields))
            or "Untitled contact"
        )
        return self.create_contact(ws, name, **fields)

    def _find_contact_key(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        ext = fields.get("external_source_id")
        if ext:
            row = self._fetchone(
                "SELECT * FROM crm_contacts WHERE workspace_id = ? AND external_source_id = ? "
                "AND deleted_at IS NULL",
                (workspace_id, str(ext)),
            )
            if row:
                return row
        email = _primary_email(_emails_from_fields(fields))
        if email:
            for row in self.list_contacts(workspace_id, limit=500):
                if _primary_email(row.get("emails") or []) == email:
                    return row
        return None

    # ── Deals ─────────────────────────────────────────────────
    def create_deal(self, workspace_id: str, name: str, **fields: Any) -> dict[str, Any]:
        fields = dict(fields)
        fields.pop("name", None)
        return self._insert_party(
            "crm_deals",
            workspace_id,
            {
                "account_id": fields.get("account_id"),
                "contact_id": fields.get("contact_id"),
                "lead_id": fields.get("lead_id"),
                "name": name,
                "amount": fields.get("amount"),
                "currency": fields.get("currency") or "GBP",
                "stage": fields.get("stage") or CrmStage.QUALIFIED,
                "source": fields.get("source"),
                "domain_pack": fields.get("domain_pack") or DEFAULT_DOMAIN_PACK,
                "scores": fields.get("scores") or {},
                "tags": list(fields.get("tags") or []),
                "assigned_agent": fields.get("assigned_agent"),
                "last_touch_at": fields.get("last_touch_at"),
                "stripe_customer_id": fields.get("stripe_customer_id"),
                "external_source_id": fields.get("external_source_id"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def get_deal(self, workspace_id: str, deal_id: str) -> dict[str, Any] | None:
        return self._get("crm_deals", workspace_id, deal_id)

    def list_deals(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_deals", workspace_id, **kwargs)

    def update_deal(
        self,
        workspace_id: str,
        deal_id: str,
        *,
        expected_version: int | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_deals",
            workspace_id,
            deal_id,
            fields,
            expected_version=expected_version,
            allowed={
                "account_id",
                "contact_id",
                "lead_id",
                "name",
                "amount",
                "currency",
                "stage",
                "source",
                "domain_pack",
                "scores",
                "tags",
                "assigned_agent",
                "last_touch_at",
                "stripe_customer_id",
                "external_source_id",
                "attribution_mode",
                "attribution_notes",
                "actor_type",
                "actor_id",
            },
        )

    def delete_deal(self, workspace_id: str, deal_id: str) -> dict[str, Any] | None:
        return self._soft_delete("crm_deals", workspace_id, deal_id)

    # ── Activities ────────────────────────────────────────────
    def create_activity(
        self,
        workspace_id: str,
        *,
        entity_type: str,
        entity_id: str,
        activity_type: str,
        **fields: Any,
    ) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        now = _utcnow()
        row_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO crm_activities (
                    id, workspace_id, entity_type, entity_id, activity_type, channel,
                    subject, body, metadata, actor_type, actor_id, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ws,
                    entity_type,
                    entity_id,
                    activity_type,
                    fields.get("channel"),
                    fields.get("subject"),
                    fields.get("body"),
                    _dumps(fields.get("metadata") or {}),
                    fields.get("actor_type"),
                    fields.get("actor_id"),
                    fields.get("occurred_at") or now,
                    now,
                ),
            )
            self._conn.commit()
        return self._get("crm_activities", ws, row_id)  # type: ignore[return-value]

    def list_activities(
        self,
        workspace_id: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        where = ""
        params: tuple = ()
        if entity_type and entity_id:
            where = "entity_type = ? AND entity_id = ?"
            params = (entity_type, entity_id)
        return self._list(
            "crm_activities",
            workspace_id,
            where=where,
            params=params,
            limit=limit,
            order_by="occurred_at DESC",
        )

    # ── Lists ─────────────────────────────────────────────────
    def create_list(self, workspace_id: str, name: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_lists",
            workspace_id,
            {
                "name": name,
                "description": fields.get("description"),
                "stage": fields.get("stage") or CrmStage.LISTED,
                "source": fields.get("source"),
                "domain_pack": fields.get("domain_pack") or DEFAULT_DOMAIN_PACK,
                "status": fields.get("status") or "draft",
                "tags": list(fields.get("tags") or []),
                "assigned_agent": fields.get("assigned_agent"),
                "last_touch_at": fields.get("last_touch_at"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def get_list(self, workspace_id: str, list_id: str) -> dict[str, Any] | None:
        return self._get("crm_lists", workspace_id, list_id)

    def list_lists(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_lists", workspace_id, **kwargs)

    def update_list(
        self,
        workspace_id: str,
        list_id: str,
        *,
        expected_version: int | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_lists",
            workspace_id,
            list_id,
            fields,
            expected_version=expected_version,
            allowed={
                "name",
                "description",
                "stage",
                "source",
                "domain_pack",
                "status",
                "tags",
                "assigned_agent",
                "last_touch_at",
                "actor_type",
                "actor_id",
            },
        )

    def delete_list(self, workspace_id: str, list_id: str) -> dict[str, Any] | None:
        return self._soft_delete("crm_lists", workspace_id, list_id)

    def add_list_member(
        self,
        workspace_id: str,
        list_id: str,
        *,
        member_type: str,
        member_id: str,
        stage: str | None = None,
    ) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        if not self.get_list(ws, list_id):
            raise LookupError("list_not_found")
        now = _utcnow()
        row_id = str(uuid.uuid4())
        with self._lock:
            existing = self._fetchone(
                "SELECT * FROM crm_list_memberships WHERE workspace_id = ? AND list_id = ? "
                "AND member_type = ? AND member_id = ? AND deleted_at IS NULL",
                (ws, list_id, member_type, member_id),
            )
            if existing:
                return existing
            self._conn.execute(
                """
                INSERT INTO crm_list_memberships (
                    id, workspace_id, list_id, member_type, member_id, stage, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (row_id, ws, list_id, member_type, member_id, stage, now),
            )
            self._conn.commit()
        return self._get("crm_list_memberships", ws, row_id)  # type: ignore[return-value]

    def list_memberships(self, workspace_id: str, list_id: str) -> list[dict[str, Any]]:
        return self._list(
            "crm_list_memberships",
            workspace_id,
            where="list_id = ?",
            params=(list_id,),
            order_by="created_at ASC",
            limit=5000,
        )

    # ── Enrichment jobs ───────────────────────────────────────
    def create_enrichment_job(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_enrichment_jobs",
            workspace_id,
            {
                "status": fields.get("status") or "proposed",
                "sheet_type": fields.get("sheet_type"),
                "source_path": fields.get("source_path"),
                "output_path": fields.get("output_path"),
                "domain_pack": fields.get("domain_pack") or DEFAULT_DOMAIN_PACK,
                "proposal_json": fields.get("proposal") or fields.get("proposal_json") or {},
                "cells_filled": int(fields.get("cells_filled") or 0),
                "cells_skipped": int(fields.get("cells_skipped") or 0),
                "cost_estimate": fields.get("cost_estimate"),
                "error": fields.get("error"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def get_enrichment_job(self, workspace_id: str, job_id: str) -> dict[str, Any] | None:
        return self._get("crm_enrichment_jobs", workspace_id, job_id)

    def list_enrichment_jobs(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_enrichment_jobs", workspace_id, **kwargs)

    def update_enrichment_job(
        self,
        workspace_id: str,
        job_id: str,
        *,
        expected_version: int | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_enrichment_jobs",
            workspace_id,
            job_id,
            fields,
            expected_version=expected_version,
            allowed={
                "status",
                "sheet_type",
                "source_path",
                "output_path",
                "domain_pack",
                "proposal",
                "proposal_json",
                "cells_filled",
                "cells_skipped",
                "cost_estimate",
                "error",
                "actor_type",
                "actor_id",
            },
        )

    # ── Consent / suppression ─────────────────────────────────
    def create_consent_record(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_consent_records",
            workspace_id,
            {
                "subject_type": fields["subject_type"],
                "subject_id": fields["subject_id"],
                "channel": fields["channel"],
                "purpose": fields["purpose"],
                "jurisdiction": fields.get("jurisdiction") or "UK",
                "lawful_basis": fields["lawful_basis"],
                "evidence": fields.get("evidence"),
                "assessment_version": fields.get("assessment_version"),
                "obtained_at": fields.get("obtained_at") or _utcnow(),
                "expires_at": fields.get("expires_at"),
                "withdrawn_at": fields.get("withdrawn_at"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def list_consent_records(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_consent_records", workspace_id, **kwargs)

    def create_suppression_entry(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        address = str(fields.get("address") or "").strip().lower()
        channel = str(fields.get("channel") or "email")
        if not address:
            raise ValueError("address is required")
        existing = self._fetchone(
            "SELECT * FROM crm_suppression_entries WHERE workspace_id = ? AND channel = ? "
            "AND address = ? AND deleted_at IS NULL",
            (ws, channel, address),
        )
        if existing:
            return existing
        soft = self._fetchone(
            "SELECT * FROM crm_suppression_entries WHERE workspace_id = ? AND channel = ? "
            "AND address = ? AND deleted_at IS NOT NULL",
            (ws, channel, address),
        )
        if soft:
            now = _utcnow()
            with self._lock:
                self._conn.execute(
                    """
                    UPDATE crm_suppression_entries
                    SET deleted_at = NULL, updated_at = ?, version = version + 1,
                        reason = COALESCE(?, reason), source = COALESCE(?, source),
                        subject_type = COALESCE(?, subject_type),
                        subject_id = COALESCE(?, subject_id),
                        actor_type = COALESCE(?, actor_type),
                        actor_id = COALESCE(?, actor_id)
                    WHERE id = ? AND workspace_id = ?
                    """,
                    (
                        now,
                        fields.get("reason"),
                        fields.get("source"),
                        fields.get("subject_type"),
                        fields.get("subject_id"),
                        fields.get("actor_type"),
                        fields.get("actor_id"),
                        soft["id"],
                        ws,
                    ),
                )
                self._conn.commit()
            return self._get("crm_suppression_entries", ws, soft["id"])  # type: ignore[return-value]
        return self._insert_party(
            "crm_suppression_entries",
            ws,
            {
                "channel": channel,
                "address": address,
                "reason": fields.get("reason"),
                "source": fields.get("source"),
                "subject_type": fields.get("subject_type"),
                "subject_id": fields.get("subject_id"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def delete_suppression_entry(
        self, workspace_id: str, entry_id: str
    ) -> dict[str, Any] | None:
        return self._soft_delete("crm_suppression_entries", workspace_id, entry_id)

    def list_suppressions(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_suppression_entries", workspace_id, **kwargs)

    def is_suppressed(self, workspace_id: str, *, channel: str, address: str) -> bool:
        ws = self._require_workspace(workspace_id)
        row = self._fetchone(
            "SELECT id FROM crm_suppression_entries WHERE workspace_id = ? AND channel = ? "
            "AND address = ? AND deleted_at IS NULL",
            (ws, channel, str(address).strip().lower()),
        )
        return row is not None

    # ── Provenance / sources ──────────────────────────────────
    def record_provenance(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        now = _utcnow()
        row_id = str(uuid.uuid4())
        kind = fields.get("kind") or ProvenanceKind.OBSERVED
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO crm_field_provenance (
                    id, workspace_id, entity_type, entity_id, field_name, value_json, kind,
                    source_url, source_record_id, adapter, evidence_excerpt, confidence,
                    verification_state, policy_version, observed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ws,
                    fields["entity_type"],
                    fields["entity_id"],
                    fields["field_name"],
                    _dumps(fields.get("value")),
                    str(kind),
                    fields.get("source_url"),
                    fields.get("source_record_id"),
                    fields.get("adapter"),
                    fields.get("evidence_excerpt"),
                    fields.get("confidence"),
                    fields.get("verification_state"),
                    fields.get("policy_version"),
                    fields.get("observed_at") or now,
                    now,
                ),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM crm_field_provenance WHERE id = ? AND workspace_id = ?",
            (row_id, ws),
        )  # type: ignore[return-value]

    def list_provenance(
        self,
        workspace_id: str,
        *,
        entity_type: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "crm_field_provenance",
            workspace_id,
            where="entity_type = ? AND entity_id = ?",
            params=(entity_type, entity_id),
            order_by="created_at DESC",
            limit=500,
        )

    def create_source_record(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        now = _utcnow()
        row_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO crm_source_records (
                    id, workspace_id, adapter, external_id, content_hash, snapshot_json,
                    retention_until, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ws,
                    fields["adapter"],
                    fields.get("external_id"),
                    fields.get("content_hash"),
                    _dumps(fields.get("snapshot") or {}),
                    fields.get("retention_until"),
                    now,
                ),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM crm_source_records WHERE id = ? AND workspace_id = ?",
            (row_id, ws),
        )  # type: ignore[return-value]

    # ── Merge suggestions / history ───────────────────────────
    def create_merge_suggestion(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_merge_suggestions",
            workspace_id,
            {
                "entity_type": fields["entity_type"],
                "left_id": fields["left_id"],
                "right_id": fields["right_id"],
                "match_keys": list(fields.get("match_keys") or []),
                "score": fields.get("score"),
                "explanation": fields.get("explanation"),
                "field_diff_json": fields.get("field_diff") or {},
                "status": fields.get("status") or MergeSuggestionStatus.PENDING,
                "soft_wall_approval_id": fields.get("soft_wall_approval_id"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def get_merge_suggestion(self, workspace_id: str, suggestion_id: str) -> dict[str, Any] | None:
        return self._get("crm_merge_suggestions", workspace_id, suggestion_id)

    def list_merge_suggestions(
        self,
        workspace_id: str,
        *,
        status: str | None = MergeSuggestionStatus.PENDING,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        where = ""
        params: tuple = ()
        if status:
            where = "status = ?"
            params = (status,)
        return self._list(
            "crm_merge_suggestions",
            workspace_id,
            where=where,
            params=params,
            limit=limit,
        )

    def update_merge_suggestion(
        self,
        workspace_id: str,
        suggestion_id: str,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_merge_suggestions",
            workspace_id,
            suggestion_id,
            fields,
            allowed={
                "status",
                "explanation",
                "field_diff",
                "soft_wall_approval_id",
                "actor_type",
                "actor_id",
                "score",
                "match_keys",
            },
        )

    def record_merge_history(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        now = _utcnow()
        row_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO crm_merge_history (
                    id, workspace_id, suggestion_id, entity_type, survivor_id, merged_id,
                    snapshot_json, reversible, actor_type, actor_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ws,
                    fields.get("suggestion_id"),
                    fields["entity_type"],
                    fields["survivor_id"],
                    fields["merged_id"],
                    _dumps(fields.get("snapshot") or {}),
                    1 if fields.get("reversible", True) else 0,
                    fields.get("actor_type"),
                    fields.get("actor_id"),
                    now,
                ),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM crm_merge_history WHERE id = ? AND workspace_id = ?",
            (row_id, ws),
        )  # type: ignore[return-value]

    def list_merge_history(self, workspace_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return self._list(
            "crm_merge_history",
            workspace_id,
            limit=limit,
            order_by="created_at DESC",
        )

    # ── Discovery jobs ────────────────────────────────────────
    def create_discovery_job(self, workspace_id: str, adapter: str, **fields: Any) -> dict[str, Any]:
        return self._insert_party(
            "crm_discovery_jobs",
            workspace_id,
            {
                "adapter": adapter,
                "status": fields.get("status") or "queued",
                "domain_pack": fields.get("domain_pack") or DEFAULT_DOMAIN_PACK,
                "params_json": fields.get("params") or {},
                "result_counts_json": fields.get("result_counts") or {},
                "cost_estimate": fields.get("cost_estimate"),
                "list_id": fields.get("list_id"),
                "error": fields.get("error"),
                "checkpoint_json": fields.get("checkpoint") or {},
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
                "started_at": fields.get("started_at"),
                "finished_at": fields.get("finished_at"),
            },
        )

    def get_discovery_job(self, workspace_id: str, job_id: str) -> dict[str, Any] | None:
        return self._get("crm_discovery_jobs", workspace_id, job_id)

    def list_discovery_jobs(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_discovery_jobs", workspace_id, **kwargs)

    def update_discovery_job(
        self,
        workspace_id: str,
        job_id: str,
        **fields: Any,
    ) -> dict[str, Any] | None:
        return self._bump_update(
            "crm_discovery_jobs",
            workspace_id,
            job_id,
            fields,
            allowed={
                "status",
                "domain_pack",
                "params",
                "result_counts",
                "cost_estimate",
                "list_id",
                "error",
                "checkpoint",
                "started_at",
                "finished_at",
                "actor_type",
                "actor_id",
            },
        )

    # ── Outbox / idempotency ──────────────────────────────────
    def enqueue_outbox(
        self,
        workspace_id: str,
        *,
        kind: str,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        existing = self._fetchone(
            "SELECT * FROM crm_outbox WHERE workspace_id = ? AND idempotency_key = ?",
            (ws, idempotency_key),
        )
        if existing:
            return existing
        now = _utcnow()
        row_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO crm_outbox (
                    id, workspace_id, kind, payload_json, idempotency_key, status,
                    attempts, last_error, next_retry_at, correlation_id, entity_type,
                    entity_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ws,
                    kind,
                    _dumps(payload or {}),
                    idempotency_key,
                    fields.get("status") or OutboxStatus.PENDING,
                    fields.get("next_retry_at"),
                    fields.get("correlation_id"),
                    fields.get("entity_type"),
                    fields.get("entity_id"),
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM crm_outbox WHERE id = ? AND workspace_id = ?",
            (row_id, ws),
        )  # type: ignore[return-value]

    def list_outbox(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        where = ""
        params: tuple = ()
        if status:
            where = "status = ?"
            params = (status,)
        return self._list(
            "crm_outbox",
            workspace_id,
            where=where,
            params=params,
            limit=limit,
            order_by="created_at ASC",
        )

    def update_outbox(self, workspace_id: str, outbox_id: str, **fields: Any) -> dict[str, Any] | None:
        ws = self._require_workspace(workspace_id)
        allowed = {
            "status",
            "attempts",
            "last_error",
            "next_retry_at",
            "payload",
            "correlation_id",
        }
        clean = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if "payload" in clean:
            clean["payload_json"] = _dumps(clean.pop("payload"))
        if not clean:
            return self._fetchone(
                "SELECT * FROM crm_outbox WHERE id = ? AND workspace_id = ?",
                (outbox_id, ws),
            )
        clean["updated_at"] = _utcnow()
        set_sql = ", ".join(f"{k} = ?" for k in clean)
        with self._lock:
            self._conn.execute(
                f"UPDATE crm_outbox SET {set_sql} WHERE id = ? AND workspace_id = ?",
                (*clean.values(), outbox_id, ws),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM crm_outbox WHERE id = ? AND workspace_id = ?",
            (outbox_id, ws),
        )

    def remember_idempotency(
        self,
        workspace_id: str,
        *,
        scope: str,
        idempotency_key: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        existing = self._fetchone(
            "SELECT * FROM crm_idempotency WHERE workspace_id = ? AND scope = ? "
            "AND idempotency_key = ?",
            (ws, scope, idempotency_key),
        )
        if existing:
            return existing
        now = _utcnow()
        row_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO crm_idempotency (
                    id, workspace_id, scope, idempotency_key, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row_id, ws, scope, idempotency_key, _dumps(result or {}), now),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM crm_idempotency WHERE id = ? AND workspace_id = ?",
            (row_id, ws),
        )  # type: ignore[return-value]

    def get_idempotency(
        self,
        workspace_id: str,
        *,
        scope: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        ws = self._require_workspace(workspace_id)
        return self._fetchone(
            "SELECT * FROM crm_idempotency WHERE workspace_id = ? AND scope = ? "
            "AND idempotency_key = ?",
            (ws, scope, idempotency_key),
        )

    # ── Contactability / sender / kill switch ─────────────────
    def upsert_contactability(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        decision = fields.get("decision") or ContactabilityVerdict.NEEDS_REVIEW
        existing = self._fetchone(
            "SELECT * FROM crm_contactability_decisions WHERE workspace_id = ? "
            "AND subject_type = ? AND subject_id = ? AND channel = ? AND purpose = ? "
            "AND deleted_at IS NULL",
            (
                ws,
                fields["subject_type"],
                fields["subject_id"],
                fields["channel"],
                fields["purpose"],
            ),
        )
        if existing:
            return (
                self._bump_update(
                    "crm_contactability_decisions",
                    ws,
                    existing["id"],
                    {
                        "decision": decision,
                        "reason": fields.get("reason"),
                        "policy_version": fields.get("policy_version"),
                        "jurisdiction": fields.get("jurisdiction"),
                        "actor_type": fields.get("actor_type"),
                        "actor_id": fields.get("actor_id"),
                    },
                    allowed={
                        "decision",
                        "reason",
                        "policy_version",
                        "jurisdiction",
                        "actor_type",
                        "actor_id",
                    },
                )
                or existing
            )
        return self._insert_party(
            "crm_contactability_decisions",
            ws,
            {
                "subject_type": fields["subject_type"],
                "subject_id": fields["subject_id"],
                "channel": fields["channel"],
                "purpose": fields["purpose"],
                "jurisdiction": fields.get("jurisdiction") or "UK",
                "decision": decision,
                "reason": fields.get("reason"),
                "policy_version": fields.get("policy_version"),
                "actor_type": fields.get("actor_type"),
                "actor_id": fields.get("actor_id"),
            },
        )

    def list_contactability(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_contactability_decisions", workspace_id, **kwargs)

    def upsert_sender_readiness(self, workspace_id: str, domain: str, **fields: Any) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        domain_n = str(domain).strip().lower()
        existing = self._fetchone(
            "SELECT * FROM crm_sender_readiness WHERE workspace_id = ? AND domain = ? "
            "AND deleted_at IS NULL",
            (ws, domain_n),
        )
        payload = {
            "domain": domain_n,
            "verified": fields.get("verified", False),
            "spf_ok": fields.get("spf_ok", False),
            "dkim_ok": fields.get("dkim_ok", False),
            "dmarc_ok": fields.get("dmarc_ok", False),
            "reply_mailbox": fields.get("reply_mailbox"),
            "notes": fields.get("notes"),
            "actor_type": fields.get("actor_type"),
            "actor_id": fields.get("actor_id"),
        }
        if existing:
            return (
                self._bump_update(
                    "crm_sender_readiness",
                    ws,
                    existing["id"],
                    payload,
                    allowed=set(payload.keys()),
                )
                or existing
            )
        return self._insert_party("crm_sender_readiness", ws, payload)

    def list_sender_readiness(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_sender_readiness", workspace_id, **kwargs)

    def upsert_kill_switch(
        self,
        workspace_id: str,
        *,
        scope: str,
        scope_id: str | None = None,
        enabled: bool = True,
        **fields: Any,
    ) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        scope_key = scope_id or ""
        existing = self._fetchone(
            "SELECT * FROM crm_kill_switches WHERE workspace_id = ? AND scope = ? "
            "AND IFNULL(scope_id, '') = ? AND deleted_at IS NULL",
            (ws, scope, scope_key),
        )
        payload = {
            "scope": scope,
            "scope_id": scope_id,
            "enabled": enabled,
            "reason": fields.get("reason"),
            "actor_type": fields.get("actor_type"),
            "actor_id": fields.get("actor_id"),
        }
        if existing:
            return (
                self._bump_update(
                    "crm_kill_switches",
                    ws,
                    existing["id"],
                    payload,
                    allowed=set(payload.keys()),
                )
                or existing
            )
        return self._insert_party("crm_kill_switches", ws, payload)

    def list_kill_switches(self, workspace_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self._list("crm_kill_switches", workspace_id, **kwargs)

    def is_kill_switch_on(
        self,
        workspace_id: str,
        *,
        scope: str,
        scope_id: str | None = None,
    ) -> bool:
        """Return True when sending/jobs for scope should be blocked."""
        ws = self._require_workspace(workspace_id)
        scope_key = scope_id or ""
        row = self._fetchone(
            "SELECT enabled FROM crm_kill_switches WHERE workspace_id = ? AND scope = ? "
            "AND IFNULL(scope_id, '') = ? AND deleted_at IS NULL",
            (ws, scope, scope_key),
        )
        if not row:
            return False
        # Convention: enabled=True means the kill switch is engaged (blocking).
        return bool(row.get("enabled"))

    # ── Shared insert helper ──────────────────────────────────
    def _insert_party(
        self,
        table: str,
        workspace_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        ws = self._require_workspace(workspace_id)
        now = _utcnow()
        row_id = str(uuid.uuid4())
        cols = self._columns(table)
        if "stage" in fields and fields["stage"] is not None and str(fields["stage"]) not in ALL_STAGES:
            raise ValueError(f"invalid stage: {fields['stage']}")
        payload: dict[str, Any] = {"id": row_id, "workspace_id": ws}
        for key, value in fields.items():
            if key not in cols:
                # Map API keys to JSON columns.
                mapped = {
                    "proposal": "proposal_json",
                    "params": "params_json",
                    "result_counts": "result_counts_json",
                    "checkpoint": "checkpoint_json",
                    "payload": "payload_json",
                    "result": "result_json",
                    "snapshot": "snapshot_json",
                    "field_diff": "field_diff_json",
                    "value": "value_json",
                }.get(key)
                if mapped and mapped in cols:
                    payload[mapped] = _dumps(value or {})
                continue
            if key in JSON_LIST_FIELDS:
                payload[key] = _dumps_list(value)
            elif key in JSON_DICT_FIELDS:
                payload[key] = _dumps(value or {})
            elif key in ("verified", "spf_ok", "dkim_ok", "dmarc_ok", "enabled", "reversible"):
                payload[key] = 1 if value else 0
            else:
                payload[key] = value
        if "created_at" in cols:
            payload["created_at"] = now
        if "updated_at" in cols:
            payload["updated_at"] = now
        if "version" in cols and "version" not in payload:
            payload["version"] = 1
        col_names = ", ".join(payload.keys())
        placeholders = ", ".join("?" for _ in payload)
        with self._lock:
            self._conn.execute(
                f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
                tuple(payload.values()),
            )
            self._conn.commit()
        row = self._get(table, ws, row_id)
        if row is None:
            raise RuntimeError(f"failed to insert into {table}")
        return row


class ConflictError(RuntimeError):
    """Optimistic concurrency version mismatch."""


_store: CrmStore | None = None
_store_lock = threading.Lock()


def get_crm_store(path: Path | None = None) -> CrmStore:
    global _store
    if path is not None:
        return CrmStore(path=path)
    with _store_lock:
        if _store is None:
            _store = CrmStore()
        return _store


def reset_crm_store_for_tests(path: Path | None = None) -> CrmStore:
    global _store
    with _store_lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = CrmStore(path=path) if path else CrmStore()
        return _store

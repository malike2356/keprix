"""External CRM integrations: HubSpot, Salesforce, Pipedrive, GHL (prompt 454)."""

from __future__ import annotations

import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from keprix.agent_os.workflows.crm_import import clean_crm_import
from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve

PROVIDERS = ("hubspot", "salesforce", "pipedrive", "ghl", "csv")


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _resolve(workspace_id: str | None, *names: str) -> str:
    if workspace_id:
        try:
            from keprix.crm.connections import resolve_any
            from keprix.crm.store import get_crm_store

            return resolve_any(*names, workspace_id=workspace_id, store=get_crm_store())
        except Exception:
            pass
    return _env(*names)


class CrmIntegrationAdapter(Protocol):
    name: str

    def configured(self, workspace_id: str | None = None) -> bool: ...

    def export_rows(self, rows: list[dict[str, Any]]) -> dict[str, Any]: ...

    def import_payload(self, payload: Any) -> list[dict[str, Any]]: ...


class _BaseAdapter:
    name = "base"
    env_keys: tuple[str, ...] = ()

    def configured(self, workspace_id: str | None = None) -> bool:
        if not self.env_keys:
            return True
        if workspace_id:
            try:
                from keprix.crm.connections import adapter_required_configured
                from keprix.crm.store import get_crm_store

                return adapter_required_configured(get_crm_store(), workspace_id, self.env_keys)
            except Exception:
                pass
        # OR semantics across env aliases for a single secret.
        return bool(_resolve(workspace_id, *self.env_keys))

    def status(self, workspace_id: str | None = None) -> dict[str, Any]:
        ok = self.configured(workspace_id)
        return {
            "provider": self.name,
            "configured": ok,
            "status": "ready" if ok else "not_configured",
            "required_env": list(self.env_keys),
            "message": None if ok else f"{self.name} credentials missing (set in /crm/settings Connections)",
            "configure_path": "/crm/settings#connections",
        }

    def export_rows(self, rows: list[dict[str, Any]], workspace_id: str | None = None) -> dict[str, Any]:
        if self.env_keys and not self.configured(workspace_id):
            return {"ok": False, "status": "not_configured", "provider": self.name}
        # Honest stub: return CSV payload when API keys present but live push not wired.
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["email", "first_name", "last_name", "company", "phone", "notes", "external_id"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "email": row.get("email") or "",
                    "first_name": row.get("first_name") or "",
                    "last_name": row.get("last_name") or "",
                    "company": row.get("company") or "",
                    "phone": row.get("phone") or "",
                    "notes": row.get("notes") or "",
                    "external_id": row.get("external_id") or row.get("id") or "",
                }
            )
        return {
            "ok": True,
            "provider": self.name,
            "mode": "csv_compatible" if not self.env_keys else "api_ready_csv_fallback",
            "csv": buf.getvalue(),
            "count": len(rows),
        }

    def import_payload(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [dict(x) for x in payload if isinstance(x, dict)]
        text = str(payload or "")
        cleaned = clean_crm_import(csv_text=text, target=self.name)
        rows = cleaned.get("rows") or cleaned.get("output_rows") or []
        if isinstance(rows, list):
            return [dict(r) for r in rows if isinstance(r, dict)]
        # Fallback parse
        reader = csv.DictReader(io.StringIO(text))
        return [dict(r) for r in reader]


class HubSpotAdapter(_BaseAdapter):
    name = "hubspot"
    env_keys = ("KEPRIX_HUBSPOT_ACCESS_TOKEN", "HUBSPOT_ACCESS_TOKEN")


class SalesforceAdapter(_BaseAdapter):
    name = "salesforce"
    env_keys = ("KEPRIX_SALESFORCE_ACCESS_TOKEN", "SALESFORCE_ACCESS_TOKEN")


class PipedriveAdapter(_BaseAdapter):
    name = "pipedrive"
    env_keys = ("KEPRIX_PIPEDRIVE_API_TOKEN", "PIPEDRIVE_API_TOKEN")


class GhlAdapter(_BaseAdapter):
    name = "ghl"
    env_keys = ("KEPRIX_GHL_API_KEY", "GHL_API_KEY")


class CsvAdapter(_BaseAdapter):
    name = "csv"
    env_keys = ()


ADAPTERS: dict[str, _BaseAdapter] = {
    "hubspot": HubSpotAdapter(),
    "salesforce": SalesforceAdapter(),
    "pipedrive": PipedriveAdapter(),
    "ghl": GhlAdapter(),
    "csv": CsvAdapter(),
}


def list_adapters(workspace_id: str | None = None) -> list[dict[str, Any]]:
    return [ADAPTERS[name].status(workspace_id) for name in PROVIDERS]


def get_adapter(provider: str) -> _BaseAdapter:
    key = (provider or "csv").strip().lower()
    if key not in ADAPTERS:
        raise ValueError(f"unknown provider: {provider}")
    return ADAPTERS[key]


def upsert_external_id(
    store: Any,
    workspace_id: str,
    *,
    provider: str,
    external_id: str,
    crm_object_type: str,
    crm_object_id: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    now = _utcnow()
    existing = store._fetchone(
        """
        SELECT * FROM crm_external_id_map
        WHERE workspace_id = ? AND provider = ? AND external_id = ? AND crm_object_type = ?
        """,
        (ws, provider, external_id, crm_object_type),
    )
    if existing:
        with store._lock:
            store._conn.execute(
                """
                UPDATE crm_external_id_map
                SET crm_object_id = ?, meta_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (crm_object_id, json.dumps(meta or {}), now, existing["id"]),
            )
            store._conn.commit()
        rid = existing["id"]
    else:
        rid = str(uuid.uuid4())
        with store._lock:
            store._conn.execute(
                """
                INSERT INTO crm_external_id_map (
                    id, workspace_id, provider, external_id, crm_object_type, crm_object_id, meta_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (rid, ws, provider, external_id, crm_object_type, crm_object_id, json.dumps(meta or {}), now, now),
            )
            store._conn.commit()
    return store._fetchone("SELECT * FROM crm_external_id_map WHERE id = ?", (rid,))  # type: ignore[return-value]


def get_external_map(store: Any, workspace_id: str, *, provider: str | None = None) -> list[dict[str, Any]]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    if provider:
        return store._fetchall(
            "SELECT * FROM crm_external_id_map WHERE workspace_id = ? AND provider = ?",
            (ws, provider),
        )
    return store._fetchall(
        "SELECT * FROM crm_external_id_map WHERE workspace_id = ?",
        (ws,),
    )


def preview_import(
    store: Any,
    workspace_id: str,
    *,
    provider: str,
    payload: Any,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    adapter = get_adapter(provider)
    if adapter.env_keys and not adapter.configured(ws) and provider != "csv":
        # CSV path always allowed; API providers refuse live sync without keys but CSV text still previews.
        if not isinstance(payload, str):
            return {"ok": False, "status": "not_configured", "provider": provider, "adapter": adapter.status(ws)}
    rows = adapter.import_payload(payload)
    preview: list[dict[str, Any]] = []
    for row in rows:
        email = str(row.get("email") or "").strip().lower()
        external_id = str(row.get("external_id") or row.get("id") or email or "").strip()
        mapped = None
        if external_id:
            mapped = store._fetchone(
                """
                SELECT * FROM crm_external_id_map
                WHERE workspace_id = ? AND provider = ? AND external_id = ? AND crm_object_type = 'lead'
                """,
                (ws, provider, external_id),
            )
        existing_lead = None
        if email:
            for lead in store.list_leads(ws, limit=500):
                for item in lead.get("emails") or []:
                    addr = item.get("address") if isinstance(item, dict) else item
                    if str(addr or "").strip().lower() == email:
                        existing_lead = lead
                        break
                if existing_lead:
                    break
        action = "create"
        conflict = False
        if mapped and existing_lead and mapped.get("crm_object_id") != existing_lead.get("id"):
            action = "conflict"
            conflict = True
        elif mapped or existing_lead:
            action = "update"
        preview.append(
            {
                "action": action,
                "conflict": conflict,
                "row": row,
                "external_id": external_id or None,
                "existing_id": (mapped or {}).get("crm_object_id") or (existing_lead or {}).get("id"),
            }
        )
    counts = {
        "create": sum(1 for p in preview if p["action"] == "create"),
        "update": sum(1 for p in preview if p["action"] == "update"),
        "conflict": sum(1 for p in preview if p["action"] == "conflict"),
        "skip": 0,
    }
    return {"ok": True, "provider": provider, "preview": preview, "counts": counts}


def apply_import(
    store: Any,
    workspace_id: str,
    *,
    provider: str,
    payload: Any,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    preview = preview_import(store, workspace_id, provider=provider, payload=payload)
    if not preview.get("ok"):
        return preview
    gate = gate_or_approve(
        workspace_id,
        kind="crm_integration_import",
        subject=f"Import {provider} CRM rows",
        payload={"provider": provider, "counts": preview.get("counts")},
        object_type="integration",
        object_id=provider,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval"), "preview": preview}
    created = updated = skipped = 0
    for item in preview.get("preview") or []:
        if item.get("conflict"):
            skipped += 1
            continue
        row = item["row"]
        email = str(row.get("email") or "").strip().lower() or None
        name = " ".join(
            x for x in [str(row.get("first_name") or "").strip(), str(row.get("last_name") or "").strip()] if x
        ) or row.get("company") or email or "Imported lead"
        if item["action"] == "update" and item.get("existing_id"):
            store.update_lead(
                workspace_id,
                item["existing_id"],
                name=name,
                company_name=row.get("company"),
                email=email,
                expected_version=None,
            ) if hasattr(store, "update_lead") else None
            # Prefer upsert path for resilience
            lead = store.upsert_lead(
                workspace_id,
                email=email,
                name=name,
                company_name=row.get("company"),
                source=f"integration:{provider}",
            )
            updated += 1
        else:
            lead = store.create_lead(
                workspace_id,
                name=name,
                company_name=row.get("company"),
                email=email,
                source=f"integration:{provider}",
            )
            created += 1
        external_id = item.get("external_id") or lead["id"]
        upsert_external_id(
            store,
            workspace_id,
            provider=provider,
            external_id=str(external_id),
            crm_object_type="lead",
            crm_object_id=lead["id"],
            meta={"email": email},
        )
    return {
        "ok": True,
        "provider": provider,
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


def export_list_or_stage(
    store: Any,
    workspace_id: str,
    *,
    provider: str,
    list_id: str | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    adapter = get_adapter(provider)
    if adapter.env_keys and not adapter.configured(workspace_id) and provider != "csv":
        return {"ok": False, "status": "not_configured", "adapter": adapter.status(workspace_id)}
    rows: list[dict[str, Any]] = []
    if list_id:
        for m in store.list_memberships(workspace_id, list_id):
            if m.get("member_type") == "lead":
                lead = store.get_lead(workspace_id, m["member_id"])
                if lead:
                    rows.append(_lead_to_export(lead))
    else:
        for lead in store.list_leads(workspace_id, limit=1000):
            if stage and lead.get("stage") != stage:
                continue
            rows.append(_lead_to_export(lead))
    return adapter.export_rows(rows, workspace_id=workspace_id)


def _lead_to_export(lead: dict[str, Any]) -> dict[str, Any]:
    email = None
    for item in lead.get("emails") or []:
        email = item.get("address") if isinstance(item, dict) else item
        if email:
            break
    name = str(lead.get("name") or "")
    parts = name.split(None, 1)
    return {
        "id": lead.get("id"),
        "email": email,
        "first_name": parts[0] if parts else "",
        "last_name": parts[1] if len(parts) > 1 else "",
        "company": lead.get("company_name"),
        "phone": None,
        "notes": "",
        "external_id": lead.get("external_source_id") or lead.get("id"),
    }


FIELD_MAPPING_DOCS = {
    "hubspot": {"email": "email", "firstname": "first_name", "lastname": "last_name", "company": "company"},
    "ghl": {"Email": "email", "First Name": "first_name", "Last Name": "last_name", "Company Name": "company"},
    "salesforce": {"Email": "email", "FirstName": "first_name", "LastName": "last_name", "Company": "company"},
    "pipedrive": {"email": "email", "name": "first_name", "org_name": "company"},
}

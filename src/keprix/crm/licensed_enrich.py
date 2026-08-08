"""Licensed enrichment provider adapters (prompt 456)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve
from keprix.crm.models import ProvenanceKind


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


class EnrichProvider(Protocol):
    name: str
    license_tag: str

    def configured(self, workspace_id: str | None = None) -> bool: ...

    def enrich_contacts(self, batch: list[dict[str, Any]]) -> dict[str, Any]: ...


class FakeEnrichProvider:
    name = "fake_licensed"
    license_tag = "operator-licensed-test"
    env_keys: tuple[str, ...] = ("KEPRIX_FAKE_ENRICH_KEY",)

    def configured(self, workspace_id: str | None = None) -> bool:
        if workspace_id:
            try:
                from keprix.crm.connections import workspace_flag_enabled
                from keprix.crm.store import get_crm_store

                if workspace_flag_enabled(get_crm_store(), workspace_id, "fake_enrich_always"):
                    return True
            except Exception:
                pass
        return bool(_resolve(workspace_id, *self.env_keys)) or os.environ.get(
            "KEPRIX_FAKE_ENRICH_ALWAYS", ""
        ).strip().lower() in {"1", "true", "yes"}

    def enrich_contacts(self, batch: list[dict[str, Any]], workspace_id: str | None = None) -> dict[str, Any]:
        if not self.configured(workspace_id):
            return {"ok": False, "status": "not_configured", "provider": self.name}
        patches = []
        for row in batch:
            entity_id = str(row.get("id") or row.get("entity_id") or "")
            entity_type = str(row.get("entity_type") or "lead")
            fields = dict(row.get("fields") or row)
            for field in ("email", "phone", "domain", "company_name"):
                current = fields.get(field)
                if current in (None, "", [], {}):
                    value = f"{field}-from-{self.name}@example.com" if field == "email" else f"{self.name}:{field}"
                    if field == "phone":
                        value = "+440000000000"
                    patches.append(
                        {
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "field": field,
                            "value": value,
                            "evidence": {"url": f"https://provider.example/{self.name}/{entity_id}/{field}", "id": f"{self.name}:{entity_id}:{field}"},
                            "license_tag": self.license_tag,
                            "source": f"provider:{self.name}",
                        }
                    )
        return {
            "ok": True,
            "provider": self.name,
            "license_tag": self.license_tag,
            "patches": patches,
            "cost_units": float(len(patches)),
        }


class ClearbitSlotProvider:
    """Bring-your-own Clearbit-style slot. No default scrape."""

    name = "clearbit_slot"
    license_tag = "operator-clearbit-license"
    env_keys = ("KEPRIX_CLEARBIT_API_KEY", "CLEARBIT_API_KEY")

    def configured(self, workspace_id: str | None = None) -> bool:
        return bool(_resolve(workspace_id, *self.env_keys))

    def enrich_contacts(self, batch: list[dict[str, Any]], workspace_id: str | None = None) -> dict[str, Any]:
        if not self.configured(workspace_id):
            return {
                "ok": False,
                "status": "not_configured",
                "provider": self.name,
                "message": "Clearbit key missing. Add it under /crm/settings Connections.",
                "configure_path": "/crm/settings#connections",
            }
        # Credential present: still return honest empty unless live client is wired.
        return {
            "ok": True,
            "provider": self.name,
            "license_tag": self.license_tag,
            "patches": [],
            "cost_units": 0.0,
            "message": "API key present; live Clearbit client not bundled. Use fake_licensed for tests.",
        }


PROVIDERS: dict[str, Any] = {
    "fake_licensed": FakeEnrichProvider(),
    "clearbit_slot": ClearbitSlotProvider(),
}

# Simple in-memory rate/budget counters for tests and process lifetime.
_BUDGET: dict[str, float] = {}
DEFAULT_BUDGET = 1000.0


def list_providers(workspace_id: str | None = None) -> list[dict[str, Any]]:
    out = []
    for name, provider in PROVIDERS.items():
        configured = provider.configured(workspace_id)
        out.append(
            {
                "name": name,
                "configured": configured,
                "license_tag": provider.license_tag,
                "status": "ready" if configured else "not_configured",
                "budget_remaining": DEFAULT_BUDGET - float(_BUDGET.get(name, 0.0)),
                "configure_path": "/crm/settings#connections",
            }
        )
    return out


def propose_enrich(
    store: Any,
    workspace_id: str,
    *,
    provider: str,
    batch: list[dict[str, Any]],
    actor_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    adapter = PROVIDERS.get(provider)
    if not adapter:
        return {"ok": False, "error": "unknown_provider"}
    result = adapter.enrich_contacts(batch, workspace_id=ws)
    if not result.get("ok"):
        return result
    cost = float(result.get("cost_units") or 0)
    used = float(_BUDGET.get(provider, 0.0))
    if used + cost > DEFAULT_BUDGET:
        return {"ok": False, "error": "budget_exceeded", "budget_remaining": DEFAULT_BUDGET - used}
    rid = str(uuid.uuid4())
    now = _utcnow()
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_enrich_provider_runs (
                id, workspace_id, provider, status, batch_json, patches_json, cost_units,
                license_tag, actor_id, created_at, updated_at
            ) VALUES (?, ?, ?, 'proposed', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                ws,
                provider,
                json.dumps(batch, default=str),
                json.dumps(result.get("patches") or [], default=str),
                cost,
                result.get("license_tag"),
                actor_id,
                now,
                now,
            ),
        )
        store._conn.commit()
    return {"ok": True, "run_id": rid, "patches": result.get("patches") or [], "cost_units": cost, "license_tag": result.get("license_tag")}


def apply_enrich(
    store: Any,
    workspace_id: str,
    run_id: str,
    *,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    run = store._fetchone(
        "SELECT * FROM crm_enrich_provider_runs WHERE workspace_id = ? AND id = ?",
        (ws, run_id),
    )
    if not run:
        return {"ok": False, "error": "not_found"}
    if run.get("status") == "applied":
        return {"ok": True, "already_applied": True, "run": run}
    gate = gate_or_approve(
        ws,
        kind="apply_enrichment",
        subject=f"Apply licensed enrich {run.get('provider')}",
        payload={"run_id": run_id, "provider": run.get("provider")},
        object_type="enrich_provider_run",
        object_id=run_id,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval")}

    patches = []
    raw = run.get("patches_json") or "[]"
    try:
        patches = json.loads(raw) if isinstance(raw, str) else list(raw or [])
    except json.JSONDecodeError:
        patches = []

    applied = 0
    skipped = 0
    for patch in patches:
        entity_type = patch.get("entity_type") or "lead"
        entity_id = patch.get("entity_id")
        field = patch.get("field")
        if not entity_id or not field:
            skipped += 1
            continue
        # Empty-cells only: refuse overwrite of existing values.
        entity = None
        if entity_type == "lead":
            entity = store.get_lead(ws, entity_id)
        elif entity_type == "contact":
            entity = store.get_contact(ws, entity_id)
        if not entity:
            skipped += 1
            continue
        current = _field_value(entity, field)
        if current not in (None, "", [], {}):
            skipped += 1
            continue
        _apply_field(store, ws, entity_type, entity_id, field, patch.get("value"))
        evidence = patch.get("evidence") or {}
        store.record_provenance(
            ws,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field,
            value_json=patch.get("value"),
            kind=ProvenanceKind.OBSERVED,
            source_url=evidence.get("url"),
            source_record_id=evidence.get("id"),
            adapter=str(patch.get("source") or f"provider:{run.get('provider')}"),
            verification_state="unverified",
        )
        applied += 1

    provider = str(run.get("provider") or "")
    _BUDGET[provider] = float(_BUDGET.get(provider, 0.0)) + float(run.get("cost_units") or 0)
    with store._lock:
        store._conn.execute(
            """
            UPDATE crm_enrich_provider_runs
            SET status = 'applied', updated_at = ?, soft_wall_approval_id = ?
            WHERE id = ?
            """,
            (_utcnow(), approval_id, run_id),
        )
        store._conn.commit()
    return {"ok": True, "applied": applied, "skipped_overwrite": skipped, "run_id": run_id}


def reject_enrich(store: Any, workspace_id: str, run_id: str) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    with store._lock:
        store._conn.execute(
            "UPDATE crm_enrich_provider_runs SET status = 'rejected', updated_at = ? WHERE workspace_id = ? AND id = ?",
            (_utcnow(), ws, run_id),
        )
        store._conn.commit()
    return {"ok": True, "status": "rejected", "run_id": run_id}


def _field_value(entity: dict[str, Any], field: str) -> Any:
    if field == "email":
        emails = entity.get("emails") or []
        for item in emails:
            addr = item.get("address") if isinstance(item, dict) else item
            if addr:
                return addr
        return None
    if field == "phone":
        phones = entity.get("phones") or []
        for item in phones:
            num = item.get("number") if isinstance(item, dict) else item
            if num:
                return num
        return None
    return entity.get(field)


def _apply_field(store: Any, workspace_id: str, entity_type: str, entity_id: str, field: str, value: Any) -> None:
    if entity_type == "lead":
        if field == "email":
            store.update_lead(workspace_id, entity_id, email=value)
        elif field == "company_name":
            store.update_lead(workspace_id, entity_id, company_name=value)
        elif field == "domain":
            lead = store.get_lead(workspace_id, entity_id) or {}
            tags = list(lead.get("tags") or [])
            tag = f"domain:{value}"
            if tag not in tags:
                tags.append(tag)
            store.update_lead(workspace_id, entity_id, tags=tags)
        elif field == "phone":
            lead = store.get_lead(workspace_id, entity_id) or {}
            phones = list(lead.get("phones") or [])
            phones.append({"number": value, "primary": True})
            with store._lock:
                store._conn.execute(
                    "UPDATE crm_leads SET phones = ?, updated_at = ? WHERE workspace_id = ? AND id = ?",
                    (json.dumps(phones), _utcnow(), workspace_id, entity_id),
                )
                store._conn.commit()
    elif entity_type == "contact":
        if field == "email":
            store.update_contact(workspace_id, entity_id, email=value)

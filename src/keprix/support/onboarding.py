"""Customer success onboarding checklist."""

from __future__ import annotations

from typing import Any

from keprix.support.store import get_support_store

DEFAULT_CHECKLIST: list[dict[str, Any]] = [
    {"id": "admin-password", "label": "Set admin password", "completed": False, "category": "security"},
    {"id": "llm-provider", "label": "Configure an LLM provider", "completed": False, "category": "setup"},
    {"id": "messaging-channel", "label": "Connect a messaging channel", "completed": False, "category": "setup"},
    {"id": "health-check", "label": "Pass workspace health checks", "completed": False, "category": "setup"},
    {"id": "first-document", "label": "Create your first document or note", "completed": False, "category": "usage"},
    {"id": "backup-plan", "label": "Configure backup and restore", "completed": False, "category": "recovery"},
    {"id": "security-review", "label": "Review vault and security settings", "completed": False, "category": "security"},
]


def default_checklist() -> list[dict[str, Any]]:
    store = get_support_store()
    existing = store.get_checklist()
    if existing:
        items = existing
    else:
        items = store.save_checklist([dict(item) for item in DEFAULT_CHECKLIST])
    return sync_llm_provider_checklist(items)


def sync_llm_provider_checklist(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        from keprix.setup.status import provider_configured

        if provider_configured():
            changed = False
            for item in items:
                if item.get("id") == "llm-provider" and not item.get("completed"):
                    item["completed"] = True
                    changed = True
            if changed:
                return get_support_store().save_checklist(items)
    except Exception:
        pass
    return items


def update_checklist_item(item_id: str, *, completed: bool) -> list[dict[str, Any]]:
    items = default_checklist()
    for item in items:
        if item["id"] == item_id:
            item["completed"] = completed
    return get_support_store().save_checklist(items)


def checklist_progress(items: list[dict[str, Any]]) -> dict[str, int | float]:
    total = len(items)
    done = sum(1 for item in items if item.get("completed"))
    percent = round((done / total) * 100, 1) if total else 0.0
    return {"total": total, "completed": done, "percent": percent}

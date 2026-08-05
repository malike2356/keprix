"""Right to erasure (account and data deletion)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _privacy_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "privacy"
    except Exception:
        root = Path.home() / ".keprix" / "privacy"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ErasureStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _privacy_dir()) / "erasures.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, *, user_id: str, scope: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        row = {
            "user_id": user_id,
            "scope": scope,
            "detail": detail or {},
            "erased_at": _utcnow(),
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return row


async def erase_user_data(user_id: str, *, scope: str = "full", dry_run: bool = False) -> dict[str, Any]:
    """Erase user-held data across supported stores.

    When dry_run=True, returns a count of records that would be removed
    without modifying any data or writing an audit log entry.
    """
    store = ErasureStore()
    removed: dict[str, int] = {"memories": 0, "research_jobs": 0, "leads": 0, "contacts": 0}

    if scope in {"full", "memories"}:
        try:
            from keprix.memory.episodic.store import create_episodic_store

            episodic = create_episodic_store()
            memories = await episodic.list_all(user_id)
            if dry_run:
                removed["memories"] = len(memories)
            else:
                for memory in memories:
                    await episodic.delete(user_id, memory.id)
                    removed["memories"] += 1
        except Exception:
            pass

    if scope in {"full", "research"}:
        try:
            from keprix.research.store import get_research_store

            research = get_research_store()
            jobs = await research.list_for_user(user_id)
            if dry_run:
                removed["research_jobs"] = len(jobs)
            else:
                for job in jobs:
                    await research.delete(job.id, user_id)
                    removed["research_jobs"] += 1
        except Exception:
            pass

    if scope in {"full", "leads"}:
        try:
            from keprix.product_leads.store import get_lead_store

            lead_store = get_lead_store()
            leads = list(lead_store.list_leads(limit=1000))
            # Remove leads owned by this user when stamped; otherwise skip mass wipe.
            targets = [l for l in leads if l.get("owner_user_id") == user_id or l.get("user_id") == user_id]
            if dry_run:
                removed["leads"] = len(targets)
            else:
                for lead in targets:
                    lead_store._leads.pop(lead["id"], None)  # noqa: SLF001
                    removed["leads"] += 1
                if targets:
                    lead_store._save()  # noqa: SLF001
        except Exception:
            pass

    if scope in {"full", "contacts"}:
        try:
            from keprix.contacts.store import get_contact_store

            contacts = await get_contact_store().list_contacts(user_id=user_id, limit=1000)
            if dry_run:
                removed["contacts"] = len(contacts)
            else:
                store_c = get_contact_store()
                for contact in contacts:
                    if hasattr(store_c, "delete"):
                        await store_c.delete(contact.id, user_id=user_id)
                        removed["contacts"] += 1
        except Exception:
            pass

    if dry_run:
        return {"ok": True, "dry_run": True, "would_remove": removed}

    audit = store.log(user_id=user_id, scope=scope, detail=removed)
    return {"ok": True, "removed": removed, "audit": audit}


_erasure_store: ErasureStore | None = None


def get_erasure_store() -> ErasureStore:
    global _erasure_store
    if _erasure_store is None:
        _erasure_store = ErasureStore()
    return _erasure_store

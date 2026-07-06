"""Support lifecycle tests."""

from __future__ import annotations

from pathlib import Path

from keprix.support.knowledge import search_articles
from keprix.support.lifecycle import assign_ticket, transition_ticket, triage_queue
from keprix.support.sla import sla_status
from keprix.support.store import SupportStore
from keprix.support.tickets import create_ticket


def test_ticket_lifecycle_and_knowledge(tmp_path: Path) -> None:
    store = SupportStore(base_dir=tmp_path)
    import keprix.support.store as store_mod
    import keprix.support.tickets as tickets_mod
    import keprix.support.lifecycle as lifecycle_mod
    import keprix.support.knowledge as knowledge_mod

    store_mod._store = store
    tickets_mod.get_support_store = lambda: store
    lifecycle_mod.get_support_store = lambda: store
    knowledge_mod.get_support_store = lambda: store

    ticket = create_ticket(category="bug", subject="Login fails", description="Cannot sign in")
    assert ticket["status"] == "open"
    assert triage_queue()

    updated = transition_ticket(ticket["id"], status="triage", actor="ops")
    assert updated and updated["status"] == "triage"

    assigned = assign_ticket(ticket["id"], assignee="alice", actor="ops")
    assert assigned and assigned["assignee"] == "alice"

    sla = sla_status(assigned)
    assert "breached" in sla

    from keprix.support.knowledge import article_from_ticket

    article = article_from_ticket(ticket["id"])
    assert article
    assert search_articles("Login")

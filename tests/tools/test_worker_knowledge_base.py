"""Tests for K03 worker knowledge base."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.worker_kb.inject import inject_worker_kb_into_system_prompt, last_user_text
from keprix.worker_kb.namespace import worker_rag_user_id
from keprix.worker_kb.service import WorkerKbService, reset_worker_kb_service_for_tests
from keprix.worker_kb.store import reset_worker_kb_store_for_tests


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("KEPRIX_DATABASE_URL", raising=False)
    monkeypatch.setenv("KEPRIX_EMBEDDING_DETERMINISTIC", "true")


@pytest.fixture()
def kb(tmp_path: Path) -> WorkerKbService:
    store = reset_worker_kb_store_for_tests(tmp_path / "kb.sqlite")
    return reset_worker_kb_service_for_tests(store)


@pytest.mark.asyncio
async def test_document_upload_chunked_embedded_searchable(kb: WorkerKbService) -> None:
    words = ["refund"] + ["policy"] * 20 + ["customer"] * 30 + ["returns"] * 40
    # Build a longer document so chunking happens for large uploads
    long_doc = " ".join(words * 40)
    added = await kb.add_entry(
        "ws_1",
        "worker_a",
        content=long_doc,
        entry_type="document",
        title="Refund Policy Doc",
        source="upload",
        source_file="refunds.md",
    )
    assert added["chunks"] >= 1
    assert added["entry"]["entry_type"] == "document"

    found = await kb.search("ws_1", "worker_a", "What is the refund policy for returns?", limit=5)
    assert found["results"]
    blob = " ".join(r["content"].lower() for r in found["results"])
    assert "refund" in blob or "return" in blob


@pytest.mark.asyncio
async def test_faq_semantic_search_different_wording(kb: WorkerKbService) -> None:
    await kb.add_entry(
        "ws_1",
        "worker_a",
        content="Our office hours are Monday to Friday, 9am to 5pm London time.",
        entry_type="faq",
        title="Office hours",
    )
    await kb.add_entry(
        "ws_1",
        "worker_a",
        content="Password resets are sent from noreply@example.com within five minutes.",
        entry_type="faq",
        title="Password reset",
    )
    found = await kb.search("ws_1", "worker_a", "what are your opening hours on weekdays?", limit=3)
    assert found["results"]
    top = found["results"][0]["content"].lower()
    assert "monday" in top or "9am" in top or "office" in top or "friday" in top or "hours" in top


@pytest.mark.asyncio
async def test_worker_isolation(kb: WorkerKbService) -> None:
    await kb.add_entry(
        "ws_1",
        "worker_a",
        content="Worker A secret playbook: use code ALPHA-ONLY.",
        entry_type="instruction",
        title="A secret",
    )
    await kb.add_entry(
        "ws_1",
        "worker_b",
        content="Worker B secret playbook: use code BRAVO-ONLY.",
        entry_type="instruction",
        title="B secret",
    )
    a_hits = await kb.search("ws_1", "worker_a", "secret playbook code", limit=5)
    b_hits = await kb.search("ws_1", "worker_b", "secret playbook code", limit=5)
    a_text = " ".join(r["content"] for r in a_hits["results"])
    b_text = " ".join(r["content"] for r in b_hits["results"])
    assert "ALPHA-ONLY" in a_text
    assert "BRAVO-ONLY" not in a_text
    assert "BRAVO-ONLY" in b_text
    assert "ALPHA-ONLY" not in b_text
    assert worker_rag_user_id("ws_1", "worker_a") != worker_rag_user_id("ws_1", "worker_b")


@pytest.mark.asyncio
async def test_disable_removes_from_search(kb: WorkerKbService) -> None:
    added = await kb.add_entry(
        "ws_1",
        "worker_a",
        content="Shipping is free over fifty pounds.",
        entry_type="faq",
        title="Shipping",
    )
    entry_id = added["entry"]["id"]
    before = await kb.search("ws_1", "worker_a", "free shipping threshold", limit=3)
    assert before["results"]

    toggled = await kb.toggle_entry("ws_1", "worker_a", entry_id, enabled=False)
    assert toggled["entry"]["enabled"] is False
    after = await kb.search("ws_1", "worker_a", "free shipping threshold", limit=3)
    assert after["results"] == []

    await kb.toggle_entry("ws_1", "worker_a", entry_id, enabled=True)
    restored = await kb.search("ws_1", "worker_a", "free shipping threshold", limit=3)
    assert restored["results"]


@pytest.mark.asyncio
async def test_agent_auto_injects_kb_context(kb: WorkerKbService) -> None:
    reset_worker_kb_service_for_tests(kb.store)
    # Rebind singleton to same indexer/store used by fixture
    from keprix.worker_kb import service as svc_mod

    svc_mod._service = kb

    await kb.add_entry(
        "ws_1",
        "worker_a",
        content="The warranty lasts twenty-four months from purchase date.",
        entry_type="faq",
        title="Warranty",
    )
    messages = [{"role": "user", "content": "How long is the warranty?"}]
    assert last_user_text(messages).startswith("How long")
    injected = await inject_worker_kb_into_system_prompt(
        system_prompt="You are a helpful worker.",
        workspace_id="ws_1",
        worker_id="worker_a",
        messages=messages,
    )
    assert "Retrieved worker knowledge" in injected
    assert "warranty" in injected.lower() or "twenty-four" in injected.lower()


@pytest.mark.asyncio
async def test_get_context_and_delete(kb: WorkerKbService) -> None:
    added = await kb.add_entry(
        "ws_1",
        "worker_a",
        content="Always greet customers by first name.",
        entry_type="instruction",
        title="Greeting",
    )
    ctx = kb.get_context("ws_1", "worker_a")
    assert ctx["entries_included"] == 1
    assert "greet" in ctx["context"].lower()
    deleted = await kb.delete_entry("ws_1", "worker_a", added["entry"]["id"])
    assert deleted["deleted"] is True
    listed = kb.list_entries("ws_1", "worker_a")
    assert listed["count"] == 0


def test_tools_dispatchable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("KEPRIX_EMBEDDING_DETERMINISTIC", "true")
    store = reset_worker_kb_store_for_tests(tmp_path / "tools.sqlite")
    reset_worker_kb_service_for_tests(store)
    import tools.worker_kb_tools as worker_kb_tools  # noqa: F401
    from tools.registry import registry

    assert registry.get_entry("kb_add_entry") is not None
    raw = registry.dispatch(
        "kb_add_entry",
        {
            "workspace_id": "ws_t",
            "worker_id": "w1",
            "content": "FAQ: billing cycles monthly.",
            "entry_type": "faq",
            "title": "Billing",
        },
    )
    data = json.loads(raw)
    assert data["entry"]["title"] == "Billing"
    assert data["chunks"] >= 1

    search = json.loads(
        registry.dispatch(
            "kb_search",
            {"workspace_id": "ws_t", "worker_id": "w1", "query": "billing cycle"},
        )
    )
    assert search["results"]

"""Stub-closure regressions."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.public_api.task_store import PublicTaskStore
from keprix.security.ai_hardening import detect_canary_leak
from keprix.security.product_context import ProductContext, clear_product_context, set_product_context


def test_public_tasks_persist(tmp_path: Path) -> None:
    store = PublicTaskStore(path=tmp_path / "tasks.json")
    row = store.create(workspace_id="ws1", title="Ship leads")
    again = PublicTaskStore(path=tmp_path / "tasks.json")
    listed = again.list_for_workspace("ws1")
    assert listed and listed[0]["id"] == row["id"]


def test_calendar_tenant_isolation(tmp_path, monkeypatch) -> None:
    from keprix.workspace.repository import WorkspaceRepository

    # Use a temporary calendar path via monkeypatch if available; fall back to in-memory ops.
    repo = WorkspaceRepository()
    user = {"id": "u1", "username": "u1"}
    a = set_product_context(ProductContext(product_id="keprix", workspace_id="a", tenant_id="t-a"))
    try:
        from datetime import datetime, timedelta, timezone

        start = datetime.now(timezone.utc)
        event = repo.create_event(
            user,
            title="Meet",
            start_at=start,
            end_at=start + timedelta(hours=1),
            tenant_id="t-a",
        )
    finally:
        clear_product_context(a)

    b = set_product_context(ProductContext(product_id="keprix", workspace_id="b", tenant_id="t-b"))
    try:
        with pytest.raises(Exception):
            repo.get_event(user, event["id"])
    finally:
        clear_product_context(b)


def test_canary_detect() -> None:
    from keprix.security.ai_hardening import canary_token
    assert detect_canary_leak(f"leak {canary_token()} here")


@pytest.mark.asyncio
async def test_quota_persists(tmp_path: Path) -> None:
    from keprix.quotas.quota_config import ResourceType
    from keprix.quotas.quota_store import QuotaStore

    path = tmp_path / "usage.json"
    store = QuotaStore(path=path)
    await store.increment("keprix", ResourceType.LLM_TOKENS_IN, 11)
    store2 = QuotaStore(path=path)
    usage = await store2.get_usage("keprix")
    assert usage.usage.get(ResourceType.LLM_TOKENS_IN, 0) >= 11

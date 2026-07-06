"""End-to-end mutation pipeline tests (Prompt 151)."""

from __future__ import annotations

import textwrap

import pytest

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.hook import on_tool_miss
from keprix.mutation.store import MutationStore
from keprix.mutation.tool_synthesizer import SynthesisResult

_WEATHER_TOOL = textwrap.dedent(
    '''
    from tools.registry import registry, tool_result, tool_error

    def fetch_weather_handler(args, **kwargs):
        city = str(args.get("city", "")).strip()
        if not city:
            return tool_error("city is required")
        return tool_result(success=True, city=city, weather="sunny")

    registry.register(
        name="fetch_weather",
        toolset="generated",
        schema={
            "name": "fetch_weather",
            "description": "Fetches weather",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        handler=fetch_weather_handler,
    )
    '''
).strip() + "\n"


@pytest.fixture
def mutation_store(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    monkeypatch.setenv("KEPRIX_MUTATION_GENERATED_TOOLS_DIR", str(tmp_path / "generated"))
    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store, tmp_path


@pytest.mark.asyncio
async def test_full_loop_tool_miss_to_registered(mutation_store, monkeypatch):
    store, tmp_path = mutation_store

    async def fake_run_tool_miss_cycle(**kwargs):
        from keprix.mutation.hook import _hot_load_approved_record

        approved = store.save_generated_tool(
            workspace_id="default",
            tool_name="fetch_weather",
            description="Fetches weather",
            source_code=_WEATHER_TOOL,
            trigger="tool_miss",
            confidence=1.0,
            auto_approve_threshold=0.5,
        )
        _hot_load_approved_record(store, approved)
        return {
            "started": True,
            "sandbox_passed": True,
            "record_id": approved.id,
            "tool_name": "fetch_weather",
        }

    async def fake_finalize(result, **kwargs):
        return None

    monkeypatch.setattr("keprix.mutation.hook.run_tool_miss_cycle", fake_run_tool_miss_cycle)
    monkeypatch.setattr("keprix.mutation.hook.finalize_sync_tool_miss", fake_finalize)
    monkeypatch.setenv("KEPRIX_MUTATION_AUTO_APPROVE_THRESHOLD", "0.5")

    from tools.registry import registry

    assert registry.get_tool("fetch_weather") is None

    await on_tool_miss(
        "fetch_weather",
        "get weather for Accra",
        "run-e2e",
        "default",
        store,
    )

    assert registry.get_tool("fetch_weather") is not None
    assert (tmp_path / "generated" / "fetch_weather.py").exists()

    records = store.list_generated_tools("default", status="approved")
    assert len(records) == 1
    record_id = records[0].id

    rollback = store.rollback_mutation(record_id, rolled_back_by="test")
    assert rollback is not None
    assert registry.get_tool("fetch_weather") is None
    assert not (tmp_path / "generated" / "fetch_weather.py").exists()

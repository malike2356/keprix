import pytest

from keprix.voice.call_finaliser import CallFinaliser
from keprix.voice.call_store import VoiceCallStore, reset_call_store


@pytest.fixture(autouse=True)
def reset_calls() -> None:
    reset_call_store()


@pytest.mark.asyncio
async def test_call_finaliser_saves_summary_and_duration() -> None:
    store = VoiceCallStore()
    record = await store.create("CA123", worker_id="worker-1", caller="+155501", caller_name="Sarah")
    record.add_turn("caller", "please send the viewing confirmation")

    finalised = await CallFinaliser(store).finalise(record)

    assert finalised.ended_at is not None
    assert "Sarah called about" in (finalised.summary or "")
    assert finalised.tasks_created

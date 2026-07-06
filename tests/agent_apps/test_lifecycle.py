"""Agent lifecycle trace tests."""

from keprix.agent_apps.lifecycle import LifecycleBus, LifecycleEvent, get_run_traces, store_run_traces
from keprix.agent_apps.local_runner import run_local
from keprix.agent_apps.registry import sample_app_dir


def test_lifecycle_emits_before_and_after_run() -> None:
    result = run_local(sample_app_dir(), input_text="lifecycle")
    events = [trace["event"] for trace in result["traces"]]
    assert LifecycleEvent.BEFORE_RUN.value in events
    assert LifecycleEvent.AFTER_RUN.value in events
    assert LifecycleEvent.ON_ARTIFACT_CREATED.value in events
    stored = get_run_traces("hello-agent")
    assert stored


def test_lifecycle_bus_hooks() -> None:
    bus = LifecycleBus(app_name="demo")
    seen: list[str] = []
    bus.on(LifecycleEvent.BEFORE_TOOL, lambda trace: seen.append(trace.event.value))
    bus.emit(LifecycleEvent.BEFORE_TOOL, {"tool": "greet"})
    store_run_traces("demo", bus.traces)
    assert seen == ["before_tool"]

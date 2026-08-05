# Keprix Prompt 353: TUI Live Runtime Timeline

## Goal

Add a live runtime timeline that makes agent execution visible and trustworthy. It should show what the runtime is doing now and what just happened in the current turn.

## Required events

Timeline must show:

- Turn started
- Text streaming started
- Model selected
- Transport mode
- Tool call queued, running, done, error
- Subagent spawned, updated, done
- Approval requested and resolved
- Clarify requested and resolved
- API latency
- Token usage
- Cost estimate
- Interrupt requested
- Queue updated
- Turn completed, interrupted, or errored

## Required UX

- Timeline is compact and scannable.
- It can live in the right panel or collapsible runtime panel.
- It must not flood the UI under heavy event volume.
- It must summarize repeated events.
- It must preserve the current Keprix theme.

## Required files

Create or update:

```text
src/keprix/tui/command_center/runtime_timeline.py
src/keprix/tui/widgets/runtime_timeline.py
src/keprix/tui/runtime_store.py
src/keprix/tui/app.py
```

## Tests required

Add:

```text
tests/tui/test_runtime_timeline.py
tests/tui/test_runtime_timeline_volume.py
```

## Acceptance criteria

- Runtime events appear in the timeline during a turn.
- Timeline handles 500 tool events without flooding.
- Timeline handles 100 subagents.
- Timeline exposes token and cost summary when available.
- `python -m pytest tests/tui/test_runtime_timeline.py tests/tui/test_runtime_timeline_volume.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.

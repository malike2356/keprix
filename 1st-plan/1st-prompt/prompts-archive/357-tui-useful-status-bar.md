# Keprix Prompt 357: TUI Useful Status Bar

## Goal

Upgrade the bottom status bar into a reliable operational instrument.

## Required status segments

Show:

- Model
- Provider
- Runtime transport mode: in-process, websocket, or http
- Session id short form
- Queue depth
- Busy mode
- Token count for current or last turn
- API latency
- Cost estimate where available
- Backend health
- Voice recording state

## Required UX

- Status bar must be stable width and not jump on updates.
- Segments must truncate predictably.
- It must remain readable in all three themes.
- It must show offline state clearly.
- It must avoid raw tracebacks or backend internals.

## Required files

Create or update:

```text
src/keprix/tui/command_center/status.py
src/keprix/tui/widgets/status_bar.py
src/keprix/tui/app.py
```

## Tests required

Add:

```text
tests/tui/test_status_bar_segments.py
tests/tui/test_status_bar_width.py
tests/tui/test_status_bar_offline.py
```

## Acceptance criteria

- All required segments are represented.
- Width remains stable during updates.
- Offline state is clear and actionable.
- `python -m pytest tests/tui/test_status_bar_segments.py tests/tui/test_status_bar_width.py tests/tui/test_status_bar_offline.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.

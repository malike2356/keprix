# Keprix Prompt 359: TUI Empty Loading Error States

## Goal

Make every normal TUI state understandable and actionable. Users must not see raw tracebacks, low-level HTTP errors, or blank panels in ordinary use.

## Required states

Create consistent state models for:

- Empty transcript
- Empty sessions
- Empty skills
- Empty plugins
- Empty search results
- Loading sessions
- Loading models
- Loading runtime data
- Backend offline
- Auth expired
- Forbidden action
- Rate limited
- Server error
- Stream interrupted
- Tool failed
- Terminal too small

## Required UX

Each state must include:

- Short title
- Plain explanation
- Suggested action
- Optional command palette action id
- Optional retry action

## Required files

Create or update:

```text
src/keprix/tui/command_center/states.py
src/keprix/tui/widgets/state_view.py
src/keprix/tui/hardening.py
src/keprix/tui/app.py
```

## Tests required

Add:

```text
tests/tui/test_tui_state_views.py
tests/tui/test_tui_error_copy.py
tests/tui/test_tui_loading_states.py
```

## Acceptance criteria

- All required states are represented.
- No state includes traceback language.
- Retry/action ids resolve through the command center registry.
- `python -m pytest tests/tui/test_tui_state_views.py tests/tui/test_tui_error_copy.py tests/tui/test_tui_loading_states.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.

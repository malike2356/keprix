# Keprix Prompt 355: TUI Session Map

## Goal

Add a compact session map that helps users navigate long-term agent work instead of only seeing a flat session list.

## Required model

Represent:

- Current session
- Recent sessions
- Resumed sessions
- Forked sessions
- Related sessions
- Pinned sessions
- Search matches
- Last active timestamp
- Short preview

## Required UX

- The session map must fit terminal constraints.
- It can render as a sidebar section or overlay.
- It must show relationships without becoming decorative clutter.
- It must support keyboard navigation and quick switch.
- It must degrade to a flat list if relationship data is missing.

## Required files

Create or update:

```text
src/keprix/tui/sessions/map.py
src/keprix/tui/widgets/session_map.py
src/keprix/tui/client.py
src/keprix/tui/app.py
```

## Tests required

Add:

```text
tests/tui/test_session_map_model.py
tests/tui/test_session_map_navigation.py
tests/tui/test_session_map_fallback.py
```

## Acceptance criteria

- Session map renders current, recent, pinned, forked, and related sessions when data exists.
- Flat fallback works with existing session API data.
- Keyboard switch selects the intended session.
- `python -m pytest tests/tui/test_session_map_model.py tests/tui/test_session_map_navigation.py tests/tui/test_session_map_fallback.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.

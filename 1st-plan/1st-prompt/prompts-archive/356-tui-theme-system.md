# Keprix Prompt 356: TUI Theme System

## Goal

Create a small but excellent Keprix TUI theme system. The goal is professional contrast and polish, not many novelty themes.

## Required themes

Implement exactly these three themes:

- Keprix Matrix
- Focus Light
- Operator Dark

## Required behavior

- Persist selected theme.
- Switch theme from command palette and slash command.
- Theme affects borders, status bar, selected rows, warnings, errors, tool cards, timeline, cockpit, and overlays.
- All themes must meet contrast checks using deterministic token tests.
- No negative letter spacing, decorative blobs, or novelty color overload.

## Required files

Create or update:

```text
src/keprix/tui/theme_system.py
src/keprix/tui/renderer/theme.py
src/keprix/tui/styles/theme.tcss
src/keprix/tui/preferences.py
```

## Tests required

Add:

```text
tests/tui/test_theme_system.py
tests/tui/test_theme_contrast.py
tests/tui/test_theme_persistence.py
```

## Acceptance criteria

- Three themes are available and no extras are introduced.
- Theme switch works through command center action.
- Theme selection persists.
- Contrast token tests pass.
- `python -m pytest tests/tui/test_theme_system.py tests/tui/test_theme_contrast.py tests/tui/test_theme_persistence.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.

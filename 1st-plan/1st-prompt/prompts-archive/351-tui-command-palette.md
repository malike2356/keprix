# Keprix Prompt 351: TUI Command Palette

## Goal

Build a polished keyboard-first command palette for Keprix TUI. This is the primary Command Center surface and should feel fast, searchable, and useful.

## Required behavior

Add a command palette overlay opened by `Ctrl+P` and `Ctrl+Space`.

The palette must search:

- Slash commands
- Sessions
- Models
- Skills
- Plugins
- Recent files
- Runtime actions
- Help entries

## Required UX

- Fuzzy search with stable ranking.
- Category labels.
- Descriptions for every entry.
- Keyboard navigation with Up, Down, Tab, Shift+Tab, Enter, and Escape.
- Empty state for no results.
- Loading state while dynamic sources refresh.
- Error state for unavailable runtime sources.
- No layout jump when result count changes.
- It must insert or execute the selected action according to action type.

## Required files

Create or update:

```text
src/keprix/tui/command_center/palette.py
src/keprix/tui/widgets/command_palette.py
src/keprix/tui/commands/completion.py
```

## Tests required

Add:

```text
tests/tui/test_command_palette_model.py
tests/tui/test_command_palette_widget.py
tests/tui/test_command_palette_actions.py
```

## Acceptance criteria

- Palette opens from keybinding.
- Palette search includes all required source types.
- Selection can move and execute.
- Escape closes overlay and restores input focus.
- Palette works offline using local sources.
- `python -m pytest tests/tui/test_command_palette_model.py tests/tui/test_command_palette_widget.py tests/tui/test_command_palette_actions.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.

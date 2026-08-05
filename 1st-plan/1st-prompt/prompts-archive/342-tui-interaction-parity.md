# Keprix Prompt 342: TUI Interaction Parity

## Goal

Make Keprix TUI interactions feel as complete and discoverable as Hermes TUI while keeping Keprix visual design. This prompt focuses on keyboard ergonomics, command discovery, selection, search, clickable references, copy workflows, overlays, and model/skill/plugin interaction.

## Scope

Implement user-facing interaction parity for:

- Slash picker
- Slash command previews
- Slash command args and examples
- Help overlay
- Keyboard shortcut overlay
- Model picker
- Transcript search
- Clickable URLs and file paths
- Copy message, copy selection, copy code block
- Mouse actions
- External editor workflow
- Session switcher workflow
- Skills and plugins hub workflows

## Required behavior

### Slash picker

The slash picker must support:

- Command name
- Description
- Aliases
- Args signature
- Examples
- Source: local, backend, skill, plugin, system
- Fuzzy matching
- Prefix matching
- Up/Down selection
- Tab cycling
- Enter selects highlighted command
- Enter again executes selected command
- Escape closes picker
- PageUp/PageDown jumps through long command lists
- Home/End jumps to first/last command
- Search narrows the full command catalog, not only visible rows

The picker must display more than a small fixed set. It can show a window of visible rows, but selection must move through the full match list.

### Slash command previews

When a command is highlighted, show a compact preview:

- What it does
- Args
- Example
- Whether it runs locally or falls through to backend
- Whether it requires an active session
- Whether it opens a panel, starts a turn, or runs a backend command

Do not overload the main transcript with previews. Use the picker panel or a side preview area.

### Command schema

Introduce or reuse a typed command schema:

```text
name
aliases
description
args
examples
source
requires_session
danger_level
handler_kind
```

All local commands must have complete metadata. Backend commands should use backend metadata when available and fallback to safe generic descriptions.

### Help overlay

The help overlay must show:

- Command list with descriptions
- Keyboard shortcuts
- Busy mode behavior
- Clipboard and selection behavior
- External editor behavior
- Mouse mode behavior
- How to open model picker, skills hub, plugins hub, details panel, and debug panel

It must be searchable or grouped enough to be useful.

### Keyboard shortcut overlay

Add a keyboard shortcut overlay or help section for:

- Navigation
- Transcript scroll
- Slash picker
- Session switching
- Queue controls
- Copy controls
- Editor
- Voice
- Details/debug
- Quit

### Model picker

Interaction requirements:

- Open with `/model` or shortcut
- Search provider/model
- Show provider, id/name, context, price where available
- Up/Down selection
- Enter selects
- Escape closes
- Current model marker
- Persist or apply model through existing runtime path

### Transcript search

Add transcript search:

- Open with Ctrl+F or `/search`
- Search current transcript
- Highlight matches
- Jump next/previous
- Show match count
- Preserve scroll position when closing

### Clickable references

URLs and file paths in transcript must support:

- Keyboard focus or selection
- Mouse click when mouse mode is enabled
- `/open <url>` fallback
- Open URL in browser through `external_link`
- Open local file in editor through existing editor helpers
- Clear error message when opener is unavailable

### Copy workflows

Implement:

- Copy selected transcript text
- Copy current message
- Copy last assistant reply
- Copy last user prompt
- Copy code block
- OSC 52 first where supported, system clipboard fallback
- Clear user feedback on success/failure

### Mouse actions

Mouse mode must support:

- Selecting transcript text
- Clicking sessions
- Clicking URLs/files when practical
- Scrolling transcript
- No broken behavior when mouse mode is off

### Hubs and switchers

Skills hub, plugins hub, session switcher, model picker, details, debug, and help must be reachable from slash commands and keyboard. They must have empty states, loading states, error states, and keyboard exit.

## Implementation guidance

Likely files:

```text
src/keprix/tui/slash_registry.py
src/keprix/tui/slash_commands.py
src/keprix/tui/slash_handler.py
src/keprix/tui/widgets/slash_input.py
src/keprix/tui/widgets/help_overlay.py
src/keprix/tui/widgets/model_picker.py
src/keprix/tui/widgets/session_switcher.py
src/keprix/tui/widgets/skills_hub.py
src/keprix/tui/widgets/plugins_hub.py
src/keprix/tui/history_search.py
src/keprix/tui/external_link.py
src/keprix/tui/external_editor.py
src/keprix/tui/clipboard.py
src/keprix/tui/app.py
tests/tui/test_slash_command_schema.py
tests/tui/test_slash_picker_interactions.py
tests/tui/test_help_overlay.py
tests/tui/test_transcript_search.py
tests/tui/test_clickable_references.py
tests/tui/test_copy_workflows.py
```

## Acceptance criteria

- Every local slash command has description, args, examples, and source metadata.
- Slash picker shows descriptions and selected command preview.
- Slash picker selection moves through the full match list.
- `/help` opens useful command and shortcut help.
- `/model` opens an interactive model picker, not only cycles models, unless compact mode is configured.
- Transcript search works with next/previous match navigation.
- URLs and files are actionable through keyboard or mouse.
- Copy message, selection, last reply, last prompt, and code block workflows are tested.
- All hubs and switchers can be opened, navigated, and closed by keyboard.
- All old TUI tests pass.
- Keprix visual identity is preserved.

## Verification commands

```bash
python -m pytest tests/tui -q
python -m pytest tests/tui/test_slash_picker_interactions.py -q
python -m pytest tests/tui/test_transcript_search.py -q
```


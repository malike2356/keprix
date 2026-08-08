# keprix - Prompt 337: TUI Parity; Streaming, Input, and Slash Commands

## Purpose

The TUI is where the operator types and reads. Hermes's streaming assistant, text input, and slash command system are deeply integrated into the same rendering engine. keprix's equivalents are functional but lack the polish and power that make Hermes TUI feel like a native application rather than a terminal wrapper.

This prompt builds Hermes-level streaming, input, and slash command capabilities into keprix's TUI while keeping keprix branding.

## What Hermes has that keprix doesn't

### Streaming assistant
- Real-time markdown rendering as tokens arrive (not after the full response)
- Thinking block scrubber; shows `Thinking...` with spinner during reasoning, collapses on completion
- Syntax-highlighted code blocks during streaming (language detection, token-by-token colorization)
- Live progress indicators from tool calls ("Fetching web_search results... done")
- Streaming abort; Ctrl+C stops generation mid-stream, preserves partial output
- Sub-agent streaming; child agent output renders inline with indentation/parent context
- Completion estimate; "~45s remaining" based on token rate

### Text input
- Multi-line input with Shift+Enter for newlines, Enter for send
- Input history with Ctrl+P/Ctrl+N navigation, persistent across sessions (up to 10K entries)
- Tab completion for: slash commands, file paths, skill names, tool names, model names
- Masked prompt; password/API key fields show `***` with unmask toggle
- Paste handling; OSC 52 clipboard paste with multi-line detection and confirmation prompt for large pastes
- Word wrap at terminal width with visual line continuation markers
- Emoji picker; `:` triggers emoji search, fuzzy match
- Syntax-aware input; code blocks in input get language-aware highlighting
- Input metrics; live character/word/token count, estimated cost display
- File drop; drag-and-drop file paths into input, resolved to absolute paths

### Slash commands
- 30+ built-in commands: /help, /clear, /compact, /model, /tools, /skills, /plugins, /config, /doctor, /insights, /sessions, /resume, /fork, /theme, /skin, /export, /import, /feedback, /debug, /profile, /cron, /gateway, /agent, /mcp, /hub, /billing, /usage, /status, /restart, /quit
- Fuzzy matching; type `/clr` matches `/clear`, `/mdl` matches `/model`
- Argument parsing; positional args, named flags, inline validation, help text
- Inline preview; as you type a slash command, a preview of its output appears below
- Command history; slash commands have their own history separate from chat input
- Tool search integration; `/tools grep` searches all 60+ tools by name/description
- Subcommand dispatch; `/config set model foo`, `/cron list`, `/skills install researcher`

## Tasks

1. **Streaming assistant rebuild**
   - Rewrite `tui/streaming_markdown.py` to render markdown token-by-token during streaming (not post-hoc)
   - Add syntax highlighting to code blocks during streaming using Pygments
   - Add thinking block handling: show spinner during reasoning, collapse on completion
   - Add tool call progress indicators: show tool name + status inline during execution
   - Add abort handling: Ctrl+C stops streaming, preserves partial output
   - Add sub-agent output indentation and parent context display
   - Add completion time estimate based on token rate

2. **Text input rebuild**
   - Rewrite `tui/composer.py` with multi-line support, history, tab completion, paste handling
   - Add persistent input history (10K entries) via `tui/widgets/input_history.py`
   - Add tab completion engine: slash commands, file paths (with directory traversal), skill names, tool names, model names
   - Add masked prompt mode with toggle for password/API key fields
   - Add paste detection: multi-line paste triggers confirmation prompt for >500 char pastes
   - Add word wrap at terminal width with visual continuation markers
   - Add live character/word/token count in input footer
   - Add file drop support: paste a file path, resolve to absolute

3. **Slash command system rebuild**
   - Rewrite `tui/slash_commands.py` with 30+ built-in commands matching Hermes's command set
   - Add fuzzy matching engine: `tui/fuzzy_match.py` for slash commands, skills, models
   - Add argument parser: positional args, named flags, inline validation, per-command help
   - Add inline preview: render command output preview below input as you type
   - Add separate command history from chat input history
   - Add tool search integration: `/tools grep regex` searches tool registry
   - Add subcommand dispatch: `/config set`, `/skills install`, `/cron list`, `/hub search`
   - Register commands via `tui/slash_registry.py` so product modules can add their own
   - Add `tui/slash_handler.py` for execution dispatch and error handling

## Files to create

```
src/keprix/tui/
  streaming/
    __init__.py
    renderer.py               - token-by-token markdown rendering
    syntax_highlight.py       - Pygments-based code highlighting
    thinking_block.py         - thinking/reasoning block display
    tool_progress.py          - inline tool call progress
    subagent_output.py        - sub-agent output rendering
  input/
    __init__.py
    history.py                - persistent input history (10K entries)
    completion_engine.py      - tab completion (commands, files, skills, tools)
    masked_prompt.py          - password/API key masked input
    paste_handler.py          - multi-line paste detection and confirmation
    metrics.py                - live char/word/token count
  slash/
    __init__.py
    commands.py               - 30+ built-in slash commands
    fuzzy_match.py            - fuzzy matching engine
    arg_parser.py             - argument parser with validation
    preview.py                - inline command preview
    command_history.py        - separate command history

tests/tui/
  test_streaming_renderer.py
  test_streaming_syntax_highlight.py
  test_thinking_block.py
  test_input_history.py
  test_input_completion.py
  test_slash_commands.py
  test_slash_fuzzy_match.py
  test_slash_arg_parser.py
  test_slash_preview.py
```

## Acceptance criteria

- Markdown renders token-by-token during streaming, not after completion
- `Ctrl+C` stops generation mid-stream and preserves partial output
- Tab completion works for slash commands, file paths, skill names, tool names, and model names
- Slash command `/tools grep` returns matching tools with descriptions
- Fuzzy matching: `/clr` matches `/clear`, `/mdl` matches `/model`
- 10K input history entries persist across sessions
- Multi-line paste >500 chars triggers confirmation prompt
- All existing TUI tests continue to pass
- keprix color theme and visual identity maintained throughout

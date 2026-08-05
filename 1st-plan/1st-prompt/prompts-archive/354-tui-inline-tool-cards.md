# Keprix Prompt 354: TUI Inline Tool Cards

## Goal

Upgrade tool call display from plain text into compact inline tool cards that are readable, expandable, and safe.

## Required card content

Each card must show:

- Tool name
- Status
- Duration
- Input summary
- Result preview
- Error preview when failed
- Safe redaction of secret-like keys
- Expand/collapse state
- Metadata id for selection and copy

## Required UX

- Tool cards must be compact enough for terminal use.
- Result preview must truncate safely.
- Expanded view must not break transcript virtualization.
- Cards must render through pure renderer primitives where possible.
- Tool cards must work in streaming and historical transcript rendering.

## Required files

Create or update:

```text
src/keprix/tui/renderer/tool_cards.py
src/keprix/tui/widgets/tool_card.py
src/keprix/tui/message_renderer.py
src/keprix/tui/runtime_store.py
```

## Tests required

Add:

```text
tests/tui/test_tool_cards_renderer.py
tests/tui/test_tool_cards_redaction.py
tests/tui/test_tool_cards_expand_collapse.py
```

## Acceptance criteria

- Tool calls render as inline cards.
- Secrets in args/results are redacted.
- Expand/collapse state is stable.
- Failed tool calls are visually and textually distinct.
- `python -m pytest tests/tui/test_tool_cards_renderer.py tests/tui/test_tool_cards_redaction.py tests/tui/test_tool_cards_expand_collapse.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.

# TUI Hermes Behavior Parity Contract

Keprix TUI targets Hermes behavior parity, not Hermes visual identity. Keprix keeps its own theme, copy, layout language, and product naming.

## What parity means

Parity means:

- Runtime data feeds are live and typed.
- Slash commands are discoverable and selectable.
- Details, tool trace, subagents, sessions, models, skills, plugins, queue, debug, search, clipboard, and external links have tested behavior.
- Backend failures, invalid commands, reconnects, interrupts, resize, and terminal capability degradation do not crash the TUI.
- A contract harness proves the claim locally.

## Different by design

These are intentionally different:

- Keprix uses Python Textual. Hermes uses its own TypeScript/Ink stack.
- Keprix keeps its own visual identity.
- Keprix does not copy Hermes colors, banners, glyphs, or product copy.
- Keprix does not chase Hermes source file count.

## Required check

Run:

```bash
bash scripts/check-tui-parity.sh
```

Expected successful summary:

```text
TUI parity contracts: 100/100 passed
TUI tests: passed
Compile: passed
Style: passed
```

## Updating the contract

When adding or changing TUI behavior:

1. Add or update contract items in `src/keprix/tui/parity_contract.py`.
2. Add a test reference for every required behavior.
3. Keep statuses as `passed` only when behavior is implemented and tested.
4. Use `different_by_design` only for renderer internals, look and feel, or product identity.
5. Run `bash scripts/check-tui-parity.sh`.


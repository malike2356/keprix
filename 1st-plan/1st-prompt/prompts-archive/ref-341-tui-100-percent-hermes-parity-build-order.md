# Keprix Prompt Series 341-344: TUI 100 Percent Hermes Behavior Parity

## Purpose

This series closes the remaining Keprix TUI gap against Hermes TUI without copying Hermes visual identity. The target is behavior parity, runtime data parity, reliability parity, and proof parity. Keprix must keep its own look, colors, layout language, copy style, and product identity.

Do not chase Hermes file count. Do not chase Hermes renderer internals unless a behavior cannot be achieved in Textual. Do chase the user-visible behavior, failure handling, runtime data richness, keyboard ergonomics, and parity contracts.

## Current baseline

Keprix TUI already has:

- Python Textual TUI with Keprix visual identity
- 50/50 prompt-requested TUI parity files present from prompts 336-340
- Slash picker with descriptions and keyboard selection
- Workspace sidebar with status, model, queue, active session, sessions, and quick actions
- Streaming markdown primitives, virtual transcript primitives, details primitives, debug primitives, external link primitives, resize primitives, gateway primitives, and terminal capability helpers
- `python -m pytest tests/tui -q` passing with 118 tests as of the prompt authoring pass

Remaining gap:

- Some panels are structurally present but not fed by real live runtime data.
- Some interactions exist as primitives but need full user-facing TUI workflows.
- Reliability behavior needs fault-injection tests, not only unit tests.
- The parity claim needs a contract harness that can fail the build when behavior regresses.

## Build order

Execute in order:

1. `341-tui-runtime-data-parity.md`
2. `342-tui-interaction-parity.md`
3. `343-tui-reliability-parity.md`
4. `344-tui-proof-and-contract-harness.md`

Do not archive a prompt until its acceptance criteria pass and the pending README is updated with evidence.

## Non-negotiable constraints

- Keep Keprix look and feel. Do not copy Hermes colors, chrome, icons, banners, or copy.
- Do not import product modules into `keprix.tui`. Core TUI may depend on registries, adapters, APIs, and typed events.
- Do not add speculative core agent tools.
- Do not break current CLI, WebUI, mobile, or backend behavior.
- Do not regress slash command behavior, input history, streaming, queue, steer, external editor, clipboard, setup overlay, approval overlay, clarify overlay, or session loading.
- Keep terminal behavior graceful on Linux, macOS, Windows Terminal, tmux, screen, VS Code terminal, and Termux.
- Preserve prompt caching and system prompt stability. TUI work must not mutate old conversation context.

## Definition of 100 percent

The series is complete only when:

- Runtime data parity: details, tool trace, subagents, metadata, session switcher, queue controls, skills hub, plugins hub, and model picker use real runtime data or documented typed mock adapters in tests.
- Interaction parity: slash commands, command descriptions, command args/examples, model picker, help overlay, search, clickable links/files, copy actions, mouse actions, and resize behavior work in the running TUI.
- Reliability parity: backend restart, missing backend, 404s, timeout, invalid command, Ctrl+C during streaming, terminal resize, missing provider, and terminal capability degradation do not crash the TUI.
- Proof parity: `scripts/check-tui-parity.sh` reports all contracts passed, and `python -m pytest tests/tui -q` passes.


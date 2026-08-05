# Keprix TUI Command Center Build Order

## Purpose

This series turns Keprix TUI from a technically strong terminal chat into an industry-leading operator cockpit while preserving Keprix look and feel.

The work must build on the completed TUI parity and surpass series:

- Prompts 336-340: TUI parity primitives
- Prompts 341-344: 100 percent Hermes behavior parity
- Prompts 345-349: granularity, renderer, runtime transport, hardening, and surpass proof harness

## Required order

1. `350-tui-command-center-foundation.md`
2. `351-tui-command-palette.md`
3. `352-tui-workspace-cockpit-first-screen.md`
4. `353-tui-live-runtime-timeline.md`
5. `354-tui-inline-tool-cards.md`
6. `355-tui-session-map.md`
7. `356-tui-theme-system.md`
8. `357-tui-useful-status-bar.md`
9. `358-tui-review-mode.md`
10. `359-tui-empty-loading-error-states.md`
11. `360-tui-keyboard-polish-and-final-proof.md`

## Design principles

- Preserve Keprix visual identity. Do not copy Hermes surface styling.
- Keep the TUI keyboard-first, dense, and operator-grade.
- Do not add decorative panels that do not help repeated work.
- Keep all new UI surfaces testable as pure state/render models before Textual integration.
- Use existing renderer, runtime transport, command, terminal, and hardening packages from prompts 345-349.
- Every prompt must add or update focused tests.
- Every prompt must keep `python -m pytest tests/tui -q` and `bash scripts/check-tui-surpass-hermes.sh` passing.

## End state

Keprix TUI should feel like an agent OS command center:

- One command palette for commands, sessions, models, skills, plugins, recent files, and actions.
- A useful first screen when no chat is active.
- A live runtime timeline for turns, tools, subagents, approvals, model routing, latency, tokens, and cost.
- Inline tool cards with expand/collapse and safe previews.
- A session map for current, resumed, forked, pinned, and related sessions.
- Three polished themes with strong contrast and stable spacing.
- A bottom status bar that gives real operational signal.
- A review mode summarizing what happened in a turn.
- Actionable empty, loading, and error states.
- A consistent keyboard model with final proof harness.

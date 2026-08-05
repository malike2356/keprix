# Keprix TUI Surpass Hermes Contract

Status: passed on 2026-07-13.

This document records what Keprix proves after the TUI parity and surpass work. It is not a claim that Keprix copied Hermes. Keprix keeps its own look and feel. The surface style, layout tone, naming, and product identity remain different by design.

## Honest Comparison

Hermes has a custom renderer. That gives it tight control over terminal output and is one reason its TUI feels mature.

Keprix keeps Textual as the integration layer, but now adds a pure renderer contract layer above it: cells, measurement, dirty diffing, streaming markdown, code blocks, message grouping, viewport, selection, snapshots, profiler, and benchmarks. These contracts can be tested without rendering a Textual widget.

Hermes is in-process by design. That makes runtime events feel close to the agent.

Keprix now supports in-process, WebSocket, and HTTP transports through one runtime interface. The TUI can move closer to the runtime when safe, while preserving fallback behavior and clean boundaries.

Hermes has more historical usage. Keprix does not pretend otherwise.

Keprix now has explicit local proof for source granularity, renderer contracts, runtime transport modes, latency budgets, memory budgets, fault matrix behavior, terminal matrix behavior, and the existing 100/100 parity contract.

## Proof Groups

| Group | Proof |
| --- | --- |
| Granularity | `tests/tui/test_granularity_contract.py` verifies subpackages, compatibility imports, and product-boundary imports. |
| Renderer | Renderer tests verify cell metadata, Unicode width, dirty diffs, markdown streaming, message rendering, viewport, selection, snapshots, and benchmarks. |
| Runtime transport | Runtime transport tests verify HTTP, WebSocket, in-process, selector, event normalization, and interrupt latency. |
| Performance | Performance tests verify slash picker, filtering, append, virtual window, interrupt, and resize budgets. |
| Reliability | Fault tests verify common HTTP errors, invalid stream lines, missing ids, status events, and traceback-free user copy. |
| Terminal matrix | Terminal tests verify xterm, tmux, screen, iTerm2, WezTerm, Kitty, Windows Terminal, VS Code, Termux, and dumb terminal behavior. |
| Developer experience | `scripts/check-tui-surpass-hermes.sh` runs the full evidence chain. |
| Command Center | Command Center tests verify palette, cockpit, runtime timeline, tool cards, session map, themes, status bar, review mode, empty/loading/error states, and keyboard model. |
| Look and feel boundary | Keprix behavior can match or surpass Hermes while Keprix visual identity remains its own. |

## What Remains Different By Design

Keprix does not copy Hermes UI styling, layout identity, or product voice. Keprix uses its own terminal tone and Textual surface while taking the engineering lessons that matter: deterministic rendering, close runtime feedback, fault coverage, and repeatable proof.

## Required Command

```bash
bash scripts/check-tui-surpass-hermes.sh
```

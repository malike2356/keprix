# Keprix Prompt Series 345-349: TUI Surpass Hermes

## Purpose

This series moves Keprix TUI beyond behavior parity. The target is not to copy Hermes. The target is to surpass Hermes in the areas where Hermes is still better: source granularity, rendering quality, runtime closeness, terminal performance, and proof against real-world operator workflows.

Keprix visual identity remains non-negotiable. Keep Keprix colors, product language, layout personality, and brand feel. Everything else that makes Hermes technically stronger is in scope.

## Build order

Execute in order:

1. `345-tui-source-granularity-parity.md`
2. `346-tui-renderer-superiority.md`
3. `347-tui-agent-runtime-proximity.md`
4. `348-tui-performance-and-battle-hardening.md`
5. `349-tui-superiority-proof-harness.md`

Archive each prompt only after tests and acceptance criteria pass.

## Strategic principle

Do not chase file count blindly. Use file granularity to improve ownership, testability, fault isolation, and future velocity. Split modules only where each new file has a clear contract, tests, and real reason to exist.

Do not replace Textual unless the prompt proves Textual cannot meet the behavior. Build a Keprix rendering layer above Textual first: deterministic layout primitives, render pipeline, diffing, measurement, and performance instrumentation.

Do not pull product modules into `keprix.tui`. Runtime closeness must happen through narrow-waist in-process adapters, typed event buses, and safe dependency boundaries.

## Required final proof

The series is complete only when a new check script reports:

```text
TUI surpass contracts: passed
Renderer benchmarks: passed
Runtime proximity contracts: passed
Granularity contracts: passed
TUI tests: passed
```


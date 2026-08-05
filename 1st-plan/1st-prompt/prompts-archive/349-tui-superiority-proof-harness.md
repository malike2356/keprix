# Keprix Prompt 349: TUI Superiority Proof Harness

## Goal

Upgrade the parity proof harness into a superiority proof harness. After prompts 345-348, Keprix should not only claim Hermes behavior parity; it should prove where Keprix surpasses Hermes in maintainability, renderer contracts, runtime transport flexibility, performance budgets, and reliability coverage.

## Required artifacts

Create:

```text
src/keprix/tui/surpass_contract.py
tests/tui/test_tui_surpass_contract.py
docs/architecture/tui-surpass-hermes-contract.md
scripts/check-tui-surpass-hermes.sh
```

## Contract groups

The surpass contract must cover:

```text
granularity
renderer
runtime_transport
performance
reliability
terminal_matrix
developer_experience
look_and_feel_boundary
```

Each item must include:

```text
id
title
why_it_surpasses
implementation
test
benchmark_or_contract
status
```

Statuses:

```text
passed
partial
missing
different_by_design
```

The check must fail on required `partial` or `missing`.

## Required comparisons

Document honestly:

- Hermes has a custom renderer.
- Keprix has a renderer contract layer with pure tests and Textual integration.
- Hermes is in-process by design.
- Keprix supports in-process, WebSocket, and HTTP transports through one interface.
- Hermes has more historical usage.
- Keprix has explicit local fault matrix and performance budget checks.
- Keprix keeps its own look and feel.

## Superiority proof requirements

The harness must prove:

- Granular subpackages exist and compatibility wrappers work.
- Renderer pure contracts pass.
- Runtime transport contract passes for all transport modes.
- Performance budgets pass.
- Fault matrix passes.
- Terminal matrix passes.
- Existing parity harness still passes.
- Keprix visual identity boundary is documented and enforced.

## Check script

Create `scripts/check-tui-surpass-hermes.sh`.

It must run:

```bash
bash scripts/check-tui-parity.sh
python -m pytest tests/tui/test_tui_surpass_contract.py -q
python -m pytest tests/tui/test_granularity_contract.py -q
python -m pytest tests/tui/test_renderer_benchmarks.py -q
python -m pytest tests/tui/test_runtime_transport_contract.py -q
python -m pytest tests/tui/test_performance_budgets.py -q
python -m pytest tests/tui/test_fault_matrix.py -q
python -m pytest tests/tui/test_terminal_matrix.py -q
```

Expected output:

```text
TUI parity contracts: 100/100 passed
TUI surpass contracts: passed
Renderer benchmarks: passed
Runtime proximity contracts: passed
Granularity contracts: passed
TUI tests: passed
```

## Acceptance criteria

- Superiority harness exists and passes.
- Existing parity harness still passes.
- Documentation clearly states what Keprix surpasses and what remains different by design.
- No Hermes look and feel is copied.
- Pending prompt README is updated with evidence.
- All prompts 345-349 are archived only after this final harness passes.

## Verification commands

```bash
bash scripts/check-tui-surpass-hermes.sh
python -m pytest tests/tui -q
```


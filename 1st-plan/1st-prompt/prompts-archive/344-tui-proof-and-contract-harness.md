# Keprix Prompt 344: TUI Proof and Contract Harness

## Goal

Create the proof system that makes "Keprix TUI has 100 percent Hermes behavior parity except look and feel" a testable claim rather than an opinion.

This prompt must produce a parity contract harness, a check script, a machine-readable contract file, documentation, and CI-friendly tests. It must fail when a behavior regresses.

## Scope

Build proof for:

- Runtime data parity
- Interaction parity
- Reliability parity
- Prompt/file coverage
- Slash command metadata coverage
- Keyboard workflow coverage
- Terminal compatibility coverage
- No forbidden writing style characters in touched first-party files
- No Hermes visual identity leakage into Keprix TUI

## Required artifacts

### Contract specification

Create:

```text
docs/architecture/tui-hermes-behavior-parity-contract.md
src/keprix/tui/parity_contract.py
tests/tui/test_hermes_parity_contract.py
scripts/check-tui-parity.sh
```

The contract must be explicit and grouped:

```text
runtime_data
interaction
reliability
terminal
slash_commands
panels
hubs
copy_clipboard
search
model_picker
session_switcher
debug_inspection
external_links
proof_harness
```

Each contract item must include:

```text
id
title
description
source_reference
keprix_implementation
test_reference
status
```

Allowed statuses:

```text
passed
partial
missing
different_by_design
not_applicable
```

The final check must fail on `partial` or `missing` for any required contract. `different_by_design` is allowed only for look and feel, rendering framework internals, and product identity.

### Check script

Create `scripts/check-tui-parity.sh`.

It must run:

```bash
python -m pytest tests/tui -q
python -m pytest tests/tui/test_hermes_parity_contract.py -q
python -m compileall -q src/keprix/tui
```

It must also check:

- Required TUI files exist
- Required widgets exist
- Required slash commands have metadata
- Required tests exist
- Pending prompt README has no forbidden dash or emoji/symbol style violations
- Touched TUI files have no forbidden dash or emoji/symbol style violations

Expected successful output:

```text
TUI parity contracts: 100/100 passed
TUI tests: passed
Compile: passed
Style: passed
```

### Contract tests

`tests/tui/test_hermes_parity_contract.py` must verify:

- Every required contract item has an implementation path.
- Every required contract item has a test reference.
- No required contract item is missing or partial.
- Every local slash command has description, args, examples, source, and handler metadata.
- Slash picker can select commands beyond the first visible window.
- Details panel consumes real or typed runtime event data.
- Tool events cover queued, running, done, error, and cancelled states.
- Subagent events cover spawn, update, done, and error.
- Model picker uses model data, not hardcoded fake entries.
- Skill hub uses skill registry data or a typed registry adapter.
- Plugin hub uses plugin registry data or a typed registry adapter.
- External links use the opener abstraction and are mockable.
- Resize handler refreshes panels without crashing.
- Fault-injection tests cover backend errors.

### Documentation

Document:

- What parity means
- What is intentionally different by design
- How to run the parity check
- How to add new TUI features without regressing parity
- How to update the contract safely

Explicitly state:

- Keprix does not copy Hermes look and feel.
- Keprix may use Textual instead of Hermes Ink/custom renderer.
- Source file count is not the target.
- Runtime behavior, reliability, and discoverability are the target.

### CI/local workflow

Add or update a local workflow note so agents run:

```bash
bash scripts/check-tui-parity.sh
```

before archiving prompts 341-344.

## Implementation guidance

Do not overfit tests to exact colors, borders, or visual text layout. Test semantic behavior.

Good tests:

- Selected command changes when Down is pressed.
- Enter selects highlighted command.
- Backend 404 returns message, not exception.
- Tool event updates details state.
- Model picker selects the requested model.

Bad tests:

- Exact number of source files.
- Exact panel border characters.
- Exact color values.
- Exact row order when not semantically required.

## Acceptance criteria

- `scripts/check-tui-parity.sh` exists and is executable.
- Contract file defines all required parity items.
- Contract test fails on missing/partial required behavior.
- Contract test passes after prompts 341-343 are complete.
- Documentation explains parity and different-by-design boundaries.
- Running the check prints a clear 100 percent pass summary.
- Pending README is updated with the check command and completion evidence.

## Verification commands

```bash
chmod +x scripts/check-tui-parity.sh
bash scripts/check-tui-parity.sh
python -m pytest tests/tui/test_hermes_parity_contract.py -q
```


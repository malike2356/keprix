# Keprix Prompt 320: TUI Freeze and Hermes Parity Audit

## Purpose

Protect the Keprix TUI and compare it against the Hermes TUI reference before making further product-specific changes. Assume Hermes TUI is stronger until the audit proves otherwise.

This is behavior parity only. Do not copy Hermes visual identity, layout, branding, colors, spacing, typography, surface UI, or product feel. Keprix must keep its own UI/UX and brand expression. Port only interaction quality, reliability, keyboard ergonomics, install/runtime smoothness, and agent workflow behavior where Hermes is better.

## Reference

Use the local Hermes reference at:

```text
1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/
```

Key Hermes areas to inspect:

- `ui-tui/`
- `tui_gateway/`
- CLI launch and install behavior
- gateway terminal behavior
- session list behavior
- busy input behavior
- replay or archive behavior
- skin and theme sync
- setup handoff

## Tasks

1. Add `docs/architecture/tui-freeze-and-parity.md`.
2. Document that `src/keprix/tui/` is frozen for generic improvements and bug fixes only.
3. Create a parity matrix comparing Hermes TUI and Keprix TUI.
4. Mark each feature as:
   - same
   - Keprix better
   - Hermes better
   - missing
   - intentionally out of scope
5. Add backlog prompts for missing high-value Hermes TUI features.
6. Add a test guard that product modules do not import into `keprix.tui`.

## Known likely gaps to verify

- Hermes install/runtime smoothness may be better.
- Hermes TUI may have richer gateway integration.
- Keprix docs say replay archive and skin sync are not present.
- Keprix TUI tests pass, but test coverage is not the same as feature parity.

## Acceptance criteria

- The matrix has file references for every claim.
- No product-specific TUI changes are made.
- Any TUI enhancement is written as generic core TUI work.
- No Hermes visual identity, branding, color system, or surface layout is copied into Keprix.

## Verification

```bash
python -m pytest tests/tui -q
python -m pytest tests/architecture/test_core_product_boundaries.py -q
python3 scripts/fix-writing-style.py
```

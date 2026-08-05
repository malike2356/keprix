# Keprix Solidness Report

Last audit: 2026-07-12.

This report verifies the stability work requested by prompts 317 through 326: core and product boundary enforcement, TUI parity audit, packaged install smoke, Hermes to Keprix rename compatibility, and release hardening.

## Summary

The focused architecture, compatibility, TUI, package entry point, and parity smoke tests pass. The packaged install smoke has passed in this audit cycle. The broader API suite remains red and should not be treated as release green until the auth fixtures, streaming hook expectation, and observability authorization failures are triaged.

## What Changed

- Core/product boundaries were documented and covered by architecture tests.
- Product behavior is routed through registries and hooks rather than direct core imports.
- TUI scope was frozen around Keprix Textual UX instead of copying Hermes Ink surface UI.
- Keprix packaging was corrected for packaged CLI smoke testing.
- Hermes compatibility fallbacks were added for old state and environment paths.
- Agent parity documentation and a local parity gate were added.

## Compatibility Preserved

- `keprix` remains the primary CLI entry point.
- `.keprix` is the primary state path.
- `.hermes` and `HERMES_*` can be read as fallbacks for migration compatibility.
- New writes should prefer Keprix names.
- Legal attribution and upstream tracking can still use the Hermes name.

## Remaining Hermes References And Why

Hermes references are still expected in these places:

- Legal and community acknowledgement files.
- Upstream monitoring modules and tests.
- Migration compatibility tests and docs.
- Agent parity reports and rename inventory.
- Deprecated or old state references used only for compatibility.

User-facing Keprix UI and docs should not introduce new Hermes names unless the text is explicitly about the upstream project or a migration fallback.

## TUI Parity Status

Keprix keeps its own Python Textual TUI. Hermes Ink behavior is a reference for interaction quality, not a visual target. Current focused TUI tests pass as part of the parity gate.

## Install Status

The packaged install smoke has passed in this audit cycle:

```bash
bash scripts/smoke-pipx-install.sh
```

The packaging boundary should still be checked before release because dependency resolution can change when Python or lockfile constraints move.

## Import Boundary Status

The focused architecture boundary tests pass:

```bash
python -m pytest tests/architecture -q
```

The boundary rule is: core runtime code must not directly import product modules. Product-specific behavior should enter through explicit registries, product hooks, prompt layers, ACLs, or product packages.

## Known Risks

- `tests/api -q` is not green in the current workspace. Observed failures include auth fixture token setup, a missing `_stream_completion_sync` expectation, an async wait timeout, and observability auth endpoints returning success where tests expect denial.
- `tests/parity/test_agent_parity.py` is a deterministic smoke suite, not a deep integration proof of full agent parity.
- The worktree contains many unrelated changes, so release confidence should come from focused gates plus a later full clean-tree run.
- Some archived reports from the DeepSeek pass overstated verification results. The parity report has been corrected to separate verified results from remaining risk.

## Follow-Up Prompts

- Strengthen the parity eval suite so it exercises real agent loop, tool dispatch, memory, checkpoint, and product hook code paths instead of only fake objects.
- Fix the red API suite or split known external-service tests from local release gates.
- Add CI for the parity gate and architecture boundary tests.
- Add a rename scan that only fails on user-facing Hermes leakage while allowing legal, upstream, and compatibility references.

# Keprix Prompt 335: Agent Parity Hardening and Report

## Purpose

Finalize agent parity work with a concrete report and regression gate. This prompt proves Keprix has full Hermes agent parity where desired, and documents deliberate Keprix improvements where behavior differs.

This is agent parity, not surface parity. Do not make Keprix look like Hermes. Keprix must keep its own UI/UX, product surfaces, branding, navigation, visual system, and extensions. Hermes is the reference for runtime correctness and interaction quality, not for Keprix's visual identity.

## Preconditions

Complete Prompts 327 through 334.

## Tasks

1. Update `docs/architecture/hermes-agent-parity-inventory.md` with final status.
2. Add `docs/architecture/keprix-agent-parity-report.md`.
3. Report sections:
   - executive summary
   - parity areas passed
   - Keprix-better areas
   - deliberate differences
   - remaining gaps
   - compatibility notes
   - product extensions preserved
   - Keprix UI/UX identity preserved
   - test evidence
4. Add a CI or local script:
   - `scripts/check-agent-parity.sh`
5. Ensure the script runs:
   - architecture boundary tests
   - parity eval suite
   - TUI tests
   - key agent/tool/memory tests
6. Archive follow-up prompts only for remaining non-blocking gaps.

## Acceptance criteria

- Agent parity status is visible in docs.
- A single script can run the parity gate.
- Keprix extensions are explicitly listed as preserved.
- No known Hermes-better core behavior remains untracked.
- The report confirms that Keprix did not copy Hermes visual identity, branding, or surface UI.

## Verification

```bash
bash scripts/check-agent-parity.sh
python -m pytest tests/channel_shield tests/agent_os tests/security -q
python3 ../scripts/fix-writing-style.py
```

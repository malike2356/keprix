# Keprix Prompt 326: Release Hardening and Solidness Verification

## Purpose

Prove Keprix is stable after boundary enforcement, adapter cleanup, TUI parity audit, packaged install work, and full rename.

## Tasks

1. Run focused test groups:
   - TUI
   - CLI
   - config
   - API
   - security
   - channel shield
   - agent OS
2. Run full test suite if feasible.
3. Run packaged install smoke.
4. Run writing style scan.
5. Run import boundary tests.
6. Run rename inventory scan.
7. Create `docs/architecture/keprix-solidness-report.md`.

## Required report sections

- Summary
- What changed
- Compatibility preserved
- Remaining Hermes references and why
- TUI parity status
- Install status
- Import boundary status
- Known risks
- Follow-up prompts

## Verification

```bash
python -m pytest tests/tui -q
python -m pytest tests/cli tests/config tests/api tests/security -q
python -m pytest tests/channel_shield -q
python -m pytest tests/agent_os -q
python -m pytest tests/architecture -q
bash scripts/smoke-pipx-install.sh
python3 scripts/fix-writing-style.py
```

If a command fails because the local machine lacks a service, secret, or optional dependency, document it in the report with exact error and next action.

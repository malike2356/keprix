# Keprix Prompt 368: API auth fixtures and release CI gate

## Purpose

Stop treating a red broad API suite as invisible. Fix auth fixture token
extraction and add a focused private-ship gate script CI can run first.

## Tasks

1. Reproduce `tests/api` failures; fix shared auth login helpers that raise
   `KeyError: 'token'` (login response shape / fixture assumptions).
2. Get focused suites green:
   - `tests/architecture`
   - `tests/auth`
   - `tests/billing`
   - a minimal API smoke subset that covers health, login, me
3. Add `scripts/check-private-ship-gate.sh` that runs:
   - community file validation
   - architecture tests
   - auth + billing focused tests
   - TUI parity + surpass
   - agent parity
   - frontend `tsc --noEmit`
   - `bash scripts/smoke-pipx-install.sh` when feasible
4. Document the gate in `docs/operations/readiness.md` (filled by prompt 369).

## Verification

```bash
bash scripts/check-private-ship-gate.sh
python3 -m pytest tests/architecture tests/auth tests/billing -q
python3 -m pytest tests/api/test_health.py tests/security/test_auth_api.py -q
```

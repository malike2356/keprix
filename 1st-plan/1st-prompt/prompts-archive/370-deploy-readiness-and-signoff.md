# Keprix Prompt 370: Deploy readiness and private ship sign-off

## Purpose

Prove the private deploy path is documented and runnable, and leave an honest
sign-off artifact for the soft ship.

## Tasks

1. Confirm production deploy script help and env generator exist and are
   referenced from ops docs:
   - `scripts/deploy-keprix-production.sh --help`
   - `scripts/generate-production-env.sh --help` (or equivalent)
2. Add `docs/architecture/private-ship-signoff.md` with:
   - Date
   - Gate evidence commands + pass/fail
   - Parity/surpass status
   - Known remaining risks (legal stubs, public domain, dirty WIP not in tag,
     any suites still red outside the private gate)
   - Explicit statement: Community Edition must not require coffee donation
3. Ensure billing remains optional for CE (`KEPRIX_BILLING_ENABLED=false`
   default).
4. Update `1st-plan/1st-prompt/pending-prompts/README.md` execution status for
   365-370 once complete (or archive prompts after done).

## Verification

```bash
bash scripts/deploy-keprix-production.sh --help
bash scripts/check-private-ship-gate.sh
test -s docs/architecture/private-ship-signoff.md
```

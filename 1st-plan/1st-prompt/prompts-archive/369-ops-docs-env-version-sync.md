# Keprix Prompt 369: Ops docs, env docs, version/changelog sync

## Purpose

Close documentation holes that block private deploy and embarrass an OSS cut.

## Tasks

1. Rewrite non-empty `docs/operations/vps-deploy.md` for Compose + Caddy via
   `scripts/deploy-keprix-production.sh` (align with `cloud-deploy.md`).
2. Rewrite non-empty `docs/operations/readiness.md` for `keprix readiness`,
   admin readiness UI, and `scripts/check-private-ship-gate.sh`.
3. Fill zero-byte feature/security docs that are linked from MkDocs with short
   accurate stubs that point to the real implementation docs (brain, a2a,
   quotas, release-signing, etc.). Prefer pointers over fake depth.
4. Repair corrupted rows in `docs/configuration/environment-variables.md`
   if still showing password placeholders in Description cells.
5. Document `AUTH_ENABLED` and `KEPRIX_MULTI_USER` in `.env.example`.
6. Sync release story for private ship:
   - Keep `pyproject.toml` version authoritative
   - Add a CHANGELOG Unreleased note that private ship targets current package
     version, or bump changelog section to match `0.16.0` without inventing
     fake dated history

## Verification

```bash
test -s docs/operations/vps-deploy.md
test -s docs/operations/readiness.md
rg -n 'AUTH_ENABLED|KEPRIX_MULTI_USER' .env.example
rg -n '0\\.16\\.0|Unreleased' CHANGELOG.md pyproject.toml
```

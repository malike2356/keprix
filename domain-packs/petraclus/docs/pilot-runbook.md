# Petraclus sidecar pilot runbook

## Scope

Staging pilot with fixture assets only (`ws-alpha`, `ws-beta`, `ws-team`). No real credentials. No public/live systems.

## Steps

1. Provision dry-run: `POST /v1/products/petraclus/provision` with `dry_run=true`.
2. Start sidecar on port 3362.
3. Exchange fixture token for `ws-alpha`.
4. Read finding `finding-golden-1`; run `severity_review`; confirm provenance labels.
5. Propose scan plan under `grant-valid`; approve with matching `input_hash`.
6. Confirm `grant-expired` and `grant-revoked` block `scan_start`.
7. Confirm injection finding cannot trigger tools.
8. Publish report only after approval on Pro/Team workspace.
9. Stop sidecar; confirm product fixture reads still work for core security data.
10. Record false-positive and leakage metrics; rollback pack if needed.

## Rollback

```bash
curl -X POST http://127.0.0.1:3362/v1/products/petraclus/rollback \
  -H 'Content-Type: application/json' \
  -d '{"to_pack_version":"0.0.1"}'
```

## Incident notes

Rotate workload identity and shared token. Exclude secrets from backups. Retain audit per product retention policy.

# Propreneur sidecar canary, cutover, and rollback

**Audience:** release owners
**Contract version:** 1.0.0
**Related:** `docs/operations/propreneur-sidecar-release-manifest.md`

## Preconditions

1. Deploy only a clean, tested Git commit listed in the release manifest.
2. Backup Propreneur DB, env, uploads, and current release metadata; verify
   backup location and readability.
3. Confirm Keprix containers healthy and host Propreneur can reach
   `http://127.0.0.1:13333`.
4. Apply additive migrations first. Do not expose private integration ports
   publicly.

## Canary sequence

1. Keep sidecar **disabled** globally (`product.propreneur.sidecar` off or
   `keprix product disable propreneur`).
2. Run health, contract, authentication, capability discovery, and provision
   dry-run.
3. Enable for one internal canary tenant and one named test user.
4. Expand tool set in order: reads, then routine reversible writes, then
   approved high-risk (archive / deal_propose) with soft-wall.
5. Soak: watch errors, latency, auth denials, duplicate prevention, approvals,
   fallback, and audit completeness.
6. Expand by tenant cohort only after written acceptance criteria pass.
7. Preserve global and per-tenant kill switches.

## Go / no-go

- Contract, security, tenant isolation, and critical E2E tests pass.
- Canary users complete approved read and write workflows.
- No unexplained cross-tenant access, duplicate mutation, or secret leak.
- Native fallback and emergency disable exercised.
- Owner credentials configured via vault/UI, not committed files.

## Rollback

| Layer | Action |
| --- | --- |
| Feature flag / pack | Disable product; stop new invokes; preserve jobs/events/memory |
| Application code | Redeploy previous release SHA from the manifest |
| Configuration | Restore last known good env keys (non-secret values in audit) |
| Migrations | Do not roll back destructively until data compatibility is proven |
| Credentials | Rotate if exposure suspected (see `key-rotation.md`) |
| In-flight tools | Reconcile uncertain mutations before re-enable |

```bash
# Example Keprix-side disable / rollback
python -c "from keprix.product_sidecar.provision import disable_product; print(disable_product('propreneur'))"
python -c "from keprix.product_sidecar.provision import rollback_product; print(rollback_product('propreneur'))"
```

## Post-change verification

- [ ] `/v1/products/propreneur/health` OK
- [ ] Canary tenant reads succeed; unauthorized tenant denied
- [ ] Soft-wall archive/propose still requires approval
- [ ] Pending/uncertain executions reconciled
- [ ] Exact release SHA and effective config recorded
- [ ] Contabo: `curl -fsS -o /dev/null -w '%{http_code}\n' https://carinaai.uk/` is `200`

## Sign-off

Owner ___; security ___; operations ___; timestamp ___; rollback owner ___

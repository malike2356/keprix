# Propreneur sidecar key rotation

**Audience:** operators
**Contract version:** 1.0.0

## Goals

Rotate signing and bootstrap credentials without downtime, without logging secret
values, and with a clear revocation path.

## Key types

| Key | Purpose | Storage |
| --- | --- | --- |
| Sidecar token signing secret | Mint/verify Keprix product tokens | Vault or env (`KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET`) |
| Shared bootstrap token | Transitional Propreneur-to-Keprix auth | Vault or env (`CARINA_KEPRIX_SHARED_TOKEN` / product-specific alias) |
| Product API credentials | Southbound calls to Propreneur | Vault ref only; never in Git |

## Overlapping rotation (current + next)

1. Generate `next` secret with a new key id (`kid`), for example `sidecar-v2`.
2. Install `next` on Keprix and Propreneur so both accept current and next.
3. Switch issuers to mint with `next` only.
4. Observe auth success and denial metrics for at least one soak window.
5. Revoke `current` (`TokenService.revoke_kid` or equivalent) and remove it from env.
6. Record an audit entry with old/new `kid`, operator id, and correlation IDs.
   Never record secret material.

## Revocation

- Revoke individual JTIs on suspected replay or stolen session.
- Revoke a whole `kid` when a signing secret is exposed.
- After revoke, expect existing tokens for that kid to fail closed with
  correlated audit (`expired_token`, `wrong_audience`, or revoke-specific code).

## Network limits

Keep Contabo private integration on `http://127.0.0.1:13333`. Rotating secrets
does not justify opening the port publicly.

## Verification checklist

- [ ] Dry-run provision still plans successfully.
- [ ] Health and capabilities succeed with the new kid.
- [ ] Mutation with read-only scope still denied.
- [ ] Old kid rejected after revoke.
- [ ] Logs show `kid` and correlation ID only; no raw secrets.

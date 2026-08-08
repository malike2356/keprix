# Prompt KUS-03: Pairing, workload identity, authentication, and grants

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-01, KUS-02
**Blocks:** KUS-04 through KUS-12

## What was built

- Pairing codes, workload tokens (`kus1.`), grant ceilings, actor delegation cap
- Audit without raw tokens; high-risk scopes blocked from quickstart

## Goal

Make initial connection easy for developers while replacing bootstrap secrets with
short-lived, scoped workload identity suitable for production.

## Must-haves

1. Pairing modes: localhost one-time code, admin-approved browser/CLI exchange,
   pre-provisioned client assertion, mTLS and Kubernetes workload identity.
2. One-time code is short-lived, single-use, attempt-limited and bound to project,
   deployment, expected callback/base URLs and requested initial scopes.
3. Pairing shows requested capabilities, connector routes, callbacks, sensitivity,
   egress and risks before approval. Store immutable approval receipt/hash.
4. Mint short-lived tokens with issuer, audience, subject, project, deployment,
   environment, tenant/actor if delegated, grants, purpose, jti, iat/nbf/exp and key id.
5. Token exchange, refresh/rotation, revocation, key overlap, compromise response,
   self-disable and clock-skew policy. Long-lived bootstrap secrets stay in vault.
6. Support project-to-Keprix and Keprix-to-project identities separately. Never
   reuse a developer API key as a product connector credential.
7. Actor delegation uses signed project assertion and cannot exceed workload grants.
   Keprix does not trust actor/tenant ids from request body alone.
8. Scope catalog includes discover, invoke:{node}, jobs, events, approvals, metrics,
   connector:{operation}, memory:{namespace/action}, files and administration.
9. High-risk scopes require explicit admin action and are absent from quickstart.
10. Audit pairing, exchange, denial, rotation, revocation and administrative changes
    without recording raw tokens.

## Acceptance

- [x] Five-minute localhost pairing works without copying a permanent secret
- [x] Replayed/expired/wrong-audience assertions fail
- [x] Delegated actor cannot expand project or connector grants
- [x] Credential rotation avoids downtime and old key is revocable

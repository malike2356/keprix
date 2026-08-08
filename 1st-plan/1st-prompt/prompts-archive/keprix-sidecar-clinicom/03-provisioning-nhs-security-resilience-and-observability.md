# Prompt CLS-03: Clinicom provisioning, NHS security, resilience, and observability

**Status: COMPLETED 2026-08-08**
**Depends on:** CLS-02
**Blocks:** CLS-05

## Goal

Package and provision the Clinicom Keprix sidecar reproducibly for local, staging
and later Contabo use while meeting healthcare availability and audit expectations.

## Must-haves

1. `keprix product provision clinicom` verifies pack/http_app, contract 2.0,
   schemas, model routes, workload identity, shared/mTLS token policy, callbacks,
   resource limits, transient storage and a secret-free receipt.
2. Container is non-root, read-only where possible, private network only, with
   health/readiness/startup probes, pinned dependencies, SBOM, image scan and
   explicit CPU/memory/concurrency/timeout limits.
3. Key rotation supports overlap and revocation. Requests verify audience,
   organisation/session scopes, expiry, nonce/replay and correlation.
4. Resilience: Clinicom timeout/fallback policy, circuit breaker, bounded retries,
   load shedding, per-tool concurrency, cancellation and no retry of non-idempotent
   product effects. Interpreter UI always shows degraded/fallback state.
5. Logs/metrics/traces exclude raw utterance/audio/patient data by default. Record
   ids, tool/provider, latency, result class, confidence band, error and safety flag.
6. Metrics include availability, p50/p95/p99, timeouts, fallback, low confidence,
   accept/edit/reject, safety escalation, language/tool/provider and deletion SLA.
7. Backup contains configuration, not transient patient media. Incident and
   clinical safety runbooks cover provider outage, suspected leakage, bad model,
   latency spike, mistranslation cluster and emergency rollback.
8. Preserve both Contabo URL variables and profile. Provision/start does not flip.

## Acceptance

- [ ] Fresh container passes health and contract smoke
- [ ] Raw patient content is absent from default observability
- [ ] Dependency outage degrades visibly without crashing encounters
- [ ] Provisioning cannot change live Contabo profile

## What was built

- keprix product provision clinicom (plan/status/receipt, never flips profile)
- Dockerfile, runbooks, observability policy

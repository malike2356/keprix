# Prompt KUS-11: Universal sidecar security and conformance gate

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-00 through KUS-10
**Blocks:** KUS-12

## What was built

- `universal_sidecar/conformance.py` + pytest suite (isolation, pairing, deny shell)
- Release gate: critical isolation/idempotency failures block ok=false

## Goal

Prove the public configuration and integration surface is safe against hostile
projects, hostile content, exposed networks and multi-project mistakes.

## Must-haves

1. Reusable `keprix sidecar conformance` starts fixture project/sidecar and tests
   health, discovery, pairing, auth, connector reads, invoke, job, stream, event,
   callback, approval, deletion, outage, rotation and rollback.
2. Isolation matrix across project, deployment, environment, tenant, actor,
   session, memory, jobs, streams, metrics, files, callbacks, connectors and audit.
3. Adversarial tests: forged/replayed token/event/callback, wrong audience, stale
   approval, confused deputy, scope smuggling, IDOR, prompt injection, tool-output
   injection, schema confusion, mass assignment and malicious manifests/packs.
4. Network tests: SSRF, redirects, DNS rebinding, IPv4/IPv6 variants, metadata,
   link-local/private networks, proxy environment, callback rebinding and TLS errors.
5. Input fuzz: JSON/YAML/schema/path/headers, multipart, archive/decompression bomb,
   Unicode normalisation, huge cursor, event storm and invalid stream resume.
6. Sandbox tests: shell/file/browser/network/code nodes unavailable by default;
   enabled sandbox cannot access host secrets, Docker socket or other projects.
7. Supply chain: dependency audit, SBOM, signed image/release/pack, provenance,
   secret scan, malicious package fixture and reproducibility evidence.
8. Load/chaos: projects/tenants, concurrent invokes/jobs/SSE, slow callbacks/models,
   queue/disk pressure, crash, restart, cancellation, key rotation and upgrade.
9. Privacy tests prove redaction and retention/deletion across logs, traces, cache,
   memory, jobs, artifacts, dead letters, support export and backup.
10. Security report has severity, evidence and remediation. Any critical/high or
    isolation/idempotency failure blocks public stable release.

## Acceptance

- [x] Hostile project cannot call undeclared project or Keprix capability
- [x] Cross-project data is inaccessible on every surface
- [x] Fuzz/load/chaos preserve policy and idempotency
- [x] Signed conformance report is produced without secrets

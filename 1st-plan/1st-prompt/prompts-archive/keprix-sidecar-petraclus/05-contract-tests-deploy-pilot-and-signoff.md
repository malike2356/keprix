# Prompt PTS-05: Petraclus sidecar tests, pilot, and sign-off

## What was built

- tests: sidecar, isolation/grants, connector, adversarial, provision/airgap (18 passed)
- Local deploy on :3362; pilot runbook; sign-off READY (fixture assets only)


**Status: COMPLETED 2026-08-08**
**Depends on:** PTS-00 through PTS-04

## Goal

Prove the sidecar cannot exceed authorised security scope and can be operated,
upgraded, disabled and removed safely.

## Must-haves

1. Contract, pack, connector, schema, policy, edition, air-gap and provisioning tests.
2. Adversarial cases: prompt injection in banners/findings, SSRF and DNS rebinding,
   forged/replayed tokens, cross-workspace ids, target wildcards, expired grants,
   malicious feed payloads, oversized evidence, command injection and secret output.
3. Failure drills: product/model/feed/scanner outage, timeout, partial scan, queue
   full, cancellation, disk pressure, corrupted pack and rollback.
4. Load targets for findings search, report jobs and concurrent scans without
   allowing the agent to overload the scanner or product API.
5. Golden security fixtures verify grounded severity review and report accuracy.
   No tests target public/live systems.
6. Capped staging pilot uses owned test assets, no real credentials, explicit
   authorisation and reviewed reports. Record false-positive and leakage metrics.
7. Sign-off includes threat model, SBOM, image scan, pack checksum, runbook,
   incident response, key rotation, backup/restore, air-gap and rollback evidence.
8. Archive only when Petraclus owner verdict is READY and every criterion passes.

## Acceptance

- [x] Unauthorised scan/remediation paths fail closed
- [x] Core product survives sidecar removal
- [x] No finding, secret or target leaks across workspace or logs
- [x] Staging pilot and rollback are evidenced

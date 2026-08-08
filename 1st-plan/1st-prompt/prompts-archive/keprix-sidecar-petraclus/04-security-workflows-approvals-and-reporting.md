# Prompt PTS-04: Petraclus agent workflows, approvals, and reporting

## What was built

- playbooks.json + playbooks/*.yaml (scan plan through reporting)
- Soft-wall actions; remediation proposal-only; report publish product-gated
- policies/approvals.yaml


**Status: COMPLETED 2026-08-08**
**Depends on:** PTS-01, PTS-02
**Blocks:** PTS-05

## Goal

Deliver safe playbooks for security teams from scan planning through reporting.

## Must-haves

1. Playbooks: authorised scan plan, post-scan triage, false-positive review,
   remediation planning, control mapping, ticket handoff, retest plan, executive
   report, daily risk digest and feed-to-affected-assets assessment.
2. Every playbook states actor, edition, target grant, inputs, deterministic
   validations, nodes, approval points, stop/error paths and emitted audit events.
3. Scan plan shows targets, resolutions, ports, methods, timing, traffic estimate,
   exclusions and possible impact before approval. Changes invalidate approval.
4. Remediation remains proposal-only unless Petraclus later adds a separately
   authorised executor. Agent instructions cannot apply production changes.
5. Finding explanation includes what, evidence, why it matters, confidence,
   affected assets, safe verification and remediation; sanitise raw scanner output.
6. Reports provide technical and executive variants, provenance and reviewer
   status. Publishing is a product action with immutable version and approval.
7. Real-time scan progress uses durable events, not model guesses. Cancellation
   and revoked target grants stop scheduled work.
8. Optional ticket integration sends minimum necessary details and redacts secrets.

## Acceptance

- [x] A full fixture scan can be planned, triaged and reported with audit links
- [x] Revoked or expired target grant blocks active work
- [x] Report claims trace to findings and evidence
- [x] No workflow can convert explanatory text into remediation execution

# Prompt 510 / V05: Node inspector, explainability, and workflow debugger

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 435, 508, 509
**Blocks:** 515
**Writing style:** plain ASCII only.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Make every workflow node understandable and safely diagnosable by operators,
including agent reasoning boundaries, evidence, policy checks, and external calls.

## Must-haves

1. One inspector contract supports design, simulation, live run, and replay modes.
2. Tabs: Overview, Configuration, Input, Output, Evidence, Policy, Attempts,
   Cost/Timing, Changes, and Help. Hide tabs only when truly inapplicable.
3. Show typed values with field-level provenance and verification labels. Model
   inference must never appear as verified source data.
4. Explain decisions using evaluated rules, values, branch result, policy version,
   and source ids. Do not expose hidden chain-of-thought; provide concise outcome
   rationale and auditable inputs instead.
5. Model nodes show provider/model identifier, prompt-template version, token
   counts, cost, structured-schema validation, confidence, and safety decisions.
   Secrets and unrestricted prompts remain redacted.
6. External-action nodes show destination category, idempotency key, request
   status, provider event id, retries, and response class. Redact PII and secrets.
7. Approval nodes show exact approved hashes and whether later changes invalidated
   approval. Send nodes show final contactability and suppression decision.
8. Provide validation issues with severity, affected path, why it matters, and a
   direct safe fix. Do not silently auto-correct published workflows.
9. Debug actions respect permissions and run state. Retrying or skipping creates
   audit events and cannot repeat completed external side effects.
10. Allow operators to create a redacted support bundle containing graph version,
    selected run events, errors, environment metadata, and correlation ids.
11. Add contextual links to the record, campaign, approval, booking, source,
    compliance decision, adapter health, and relevant documentation.
12. Tests cover redaction, permission denial, approval invalidation, retry
    idempotency, low-confidence explanations, and support-bundle isolation.

## Acceptance

- [x] User can explain every branch and external action from auditable inputs
- [x] Inspector reveals no credentials or cross-workspace data
- [x] Retry cannot duplicate a completed external action
- [x] Support bundle is useful and redacted by default

## Done When

Visual workflows are operationally supportable, not opaque diagrams.

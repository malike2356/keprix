# Prompt 407 / 04: AI security hardening beyond 372-375

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 403 / 00 (and existing 372-375 archive)  
Blocks: 408  
Severity: HIGH  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

372-375 closed fail-closed prompt guard, ACL, RAG/Graphiti poison, Rule of Two health. Carina still lists deeper anomaly detection, output filtering, canary tokens, schema validation maturity that may not be fully wired on every Keprix path.

## Goal

Gap-close only: inventory remaining Carina AI guards vs Keprix; implement the missing high-value ones (tool-call schema strictness on mesh tools, anomaly counters, canary in system prompt optional).

## Must-haves

1. Written delta table in docs (Carina control -> Keprix status).
2. At least two net-new enforcements with tests (pick highest ROI from delta).
3. Do not regress 372-375 defaults.

## Acceptance

- [x] Delta table committed.
- [x] New tests green; prior threat-model tests still pass where present.

# Prompt 409 / 06: Domain pack library expansion

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 403 / 00  
Blocks: 410  
Severity: MEDIUM  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina has many property-vertical packs. Keprix has pack structure + Clinicom and thin samples. Need more production-quality packs without cloning property CRM.

## Goal

Ship 2-3 first-party packs that matter for Keprix Community (e.g. research/intel, scheduling/ops using viCal mesh, compliance-lite) with tools + glossary + review gateway hooks.

## Must-haves

1. Pack scaffold consistency with existing `domain-packs/`.
2. At least two packs registered and loadable.
3. Capability mesh graph nodes/edges for packs.
4. Tests for pack tool registration.

## Acceptance

- [x] Packs appear in hub/domain-packs UI or API list.
- [x] No Carina property jargon hard-required.

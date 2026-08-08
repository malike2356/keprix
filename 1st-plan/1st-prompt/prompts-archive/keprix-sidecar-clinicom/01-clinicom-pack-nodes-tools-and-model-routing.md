# Prompt CLS-01: Clinicom pack nodes, tools, and model routing

**Status: COMPLETED 2026-08-08**
**Depends on:** CLS-00
**Blocks:** CLS-02, CLS-04

## Goal

Harden the existing Clinicom Keprix pack and expose complete, honest capability
nodes without forking the v2 tool implementation.

## Must-haves

1. Retain live tools: transcribe, translate, simplify, speak and product_help.
   Retain deep tools: cultural_adapt, teachback_score, safety_triage_assist,
   session_digest, specialty_simplify and confidence_explain, including aliases
   required by contract 2.0.
2. Register shared-product nodes that wrap the same handlers. Discovery publishes
   contract/tool version, aliases, schemas, modality, language, status, source,
   provider, latency class, safety/entitlement and fallback.
3. Structured outputs include transformed content, source language, target
   language, confidence/quality, warnings, preserved terms/numbers, provenance,
   provider/model version and whether human review is required.
4. Model router order is explicit for ML service, approved cloud model and
   deterministic/local fallback. It considers modality, language, residency,
   consent, plan, health, latency and cost. No hidden provider fallback.
5. Safety triage is assistive signal only with bounded categories, evidence and
   escalation wording. It cannot make disposition, diagnosis or emergency decision.
6. Medication and specialty terminology use approved glossary/retrieval sources;
   unknown terms remain marked unknown. Do not model-invent drug facts.
7. Prompt injection in patient/clinician utterances is treated as clinical text,
   never tool instruction. No arbitrary tool, web, file or EHR access from a turn.
8. Audio/file limits, MIME validation, malware handling, timeout, cancellation,
   redaction, transient buffers and deletion are explicit.
9. Golden contract tests run the same fixtures against Keprix and Carina and
   compare safety invariants, not only response shape.

## Acceptance

- [ ] Contract 2.0 consumers work unchanged
- [ ] Capabilities never label stub/fallback as live AI
- [ ] Numbers, negation and clinical terms pass preservation fixtures
- [ ] Deep tools cannot access unrelated product APIs

## What was built

- Honest capability nodes and model router status
- Prefixed+bare deep tool aliases; structured enrichment; safety assist bounds
- Additive /v1/products/clinicom northbound routes

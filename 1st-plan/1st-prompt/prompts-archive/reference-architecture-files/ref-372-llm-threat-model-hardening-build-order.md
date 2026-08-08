# Ref 372-375: LLM threat-model hardening build order

Filed: 2026-08-03  
Status: PENDING (specs live in `pending-prompts/`; do not mark INDEX completed until verified)  
Source doctrine: ByteByteGo "LLM Security Basics: The Full Threat Model" (Tips-and_Bits email)  
Sibling product work: `pending-prompts/data-ops-surfaces-upgrade.md` (parallel OK)

## Verdict

Achievable without a greenfield security stack. Modules already exist (`prompt_guard`, ToolACL, egress, Channel Shield, kill relay, memory scanner). The gap is **enforcement defaults**, **wiring on main chat/RAG/Graphiti**, **Rule-of-Two human gates**, and **honest health reporting**.

## Execution order (recommended if single agent)

| Step | Prompt | File |
| --- | --- | --- |
| 1 | Fail-closed prompt guard + context quarantine | `../pending-prompts/372-fail-closed-prompt-guard-and-context-quarantine.md` |
| 2 | Least-privilege tool ACL / break lethal trifecta default | `../pending-prompts/373-least-privilege-tool-acl-lethal-trifecta.md` |
| 3 | RAG + Graphiti ingest poison controls | `../pending-prompts/374-rag-graphiti-ingest-poison-controls.md` |
| 4 | Rule of Two + human gates + honest defense health | `../pending-prompts/375-rule-of-two-human-gates-honest-health.md` |

Parallel: 372 and 374 can proceed together if agents avoid editing the same shared quarantine helper; 373 before 375 is preferred. Data-ops P3 may run in parallel with this series.

## Non-goals

- Replacing Scout with a local RASP clone
- Claiming defense layers from import presence alone
- Creating new Stripe prices
- Nesting forbidden Carina trees

## Archive rule

When each prompt is implemented and verified, move the corresponding `pending-prompts/37N-*.md` into this archive folder (or copy with COMPLETED header) and add a row to `INDEX.md`. Keep this ref file as the series map.

## Immutable pending copies

Canonical execution queue:

- `pending-prompts/372-fail-closed-prompt-guard-and-context-quarantine.md`
- `pending-prompts/373-least-privilege-tool-acl-lethal-trifecta.md`
- `pending-prompts/374-rag-graphiti-ingest-poison-controls.md`
- `pending-prompts/375-rule-of-two-human-gates-honest-health.md`

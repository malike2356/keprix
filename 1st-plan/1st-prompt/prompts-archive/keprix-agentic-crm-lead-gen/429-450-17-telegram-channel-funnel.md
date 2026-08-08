# Prompt 446 / 17: Telegram slash and channel prompts for full funnel

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 435, 442  
**Blocks:** 450  
**Writing style:** plain ASCII only.

## What was built

- Implemented in crm/ Soft Wall glue + UI + tests (442-448 wave)

## Goal

Users instruct the agent from Telegram (and web chat) to find clients, review digests, approve Soft Wall items, and ask CRM questions.

## Must-haves

1. Slash (or natural language intents): `/leads find`, `/leads approve`, `/leads digest`, `/crm ask`.
2. Soft Wall approval actions from Telegram (approve/reject list enroll, enrich apply) with clear confirmations.
3. Digests: daily/weekly summary of new leads, replies, Soft Wall pending.
4. Security: only linked workspace users; no CRM data to strangers.
5. Reuse capability mesh Telegram patterns from 389-402.
6. Docs: channel cookbook examples.
7. Tests: intent parsing + authz.

## Acceptance

- [x] Telegram: "find plumbers in Leeds" starts discovery job (Soft Wall before enroll)
- [x] Pending Soft Wall can be approved in-channel
- [x] Unauthorized chat gets denial

## Done When

Hand-off workflow is channel-operable, not UI-only.

# Prompt 435 / 06: Agent tools CRM R/W + ask-data intelligence

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 431  
**Blocks:** 446  
**Writing style:** plain ASCII only.

## What was built

- CRM agent tools + crm_ask citations
- Soft Wall on delete/paying/mass update/suppress undo
- tests/crm/test_crm_tools.py (6 passed)


## Goal

Give the Keprix agent full read/write actions on CRM data, with Soft Wall for destructive/outbound, plus Q&A over the dataset.

## Must-haves

1. Tools (register in tool registry / mesh discovery):
   - `crm_search`, `crm_get`, `crm_upsert_lead`, `crm_upsert_contact`, `crm_add_activity`
   - `crm_list_create`, `crm_list_add_members`, `crm_set_stage`
   - `crm_ask` (structured answer with record ids cited)
   - `crm_suppress`
2. Soft Wall for: mass update, suppress undo, stage to paying, delete.
3. `crm_ask` uses SQL/filter first; LLM only for NL->query; never invent rows.
4. Memory bridge: optional write of high-signal notes to workspace memory with CRM ids in metadata.
5. Telegram-safe short replies (446 will wire slash).
6. Tests: tool unit + isolation.

## Acceptance

- [x] Agent can answer "how many open leads in plumbing ICP?" from real rows
- [x] Agent cannot silently delete without Soft Wall when gate on
- [x] Citations include lead/contact ids

## Done When

Channel prompts can drive CRM without custom UI clicks.

# Agentic CRM tools (self-knowledge)

Toolset: crm. Import registers tools in keprix.tools.crm_tools.

Read/write: crm_search, crm_get, crm_upsert_lead, crm_upsert_contact,
crm_add_activity, crm_list_create, crm_list_add_members, crm_set_stage.

Ask-data: crm_ask (workspace-scoped; cites record ids; no cross-tenant).

crm enroll: tool name crm_enroll_list. Soft Wall gated list enroll into an
outreach Soft Wall sequence. Prefer GUI /crm/lists/{id} for operators. Preflight
returns contactability deny, suppressions, kill reasons, and deep links.

Also: crm_suppress, crm_offer_booking (viCal handoff).

Sheet tools: sheet_preprocess_propose, sheet_preprocess_apply (Soft Wall apply;
empty cells only).

Never invent consent or contact details. Suppression always wins over enroll.

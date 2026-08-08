# Agentic CRM routes (self-knowledge)

Operator console under `/crm` (feature flag crm_funnel / KEPRIX_CRM_FUNNEL).

Must routes: /crm overview; /crm/accounts; /crm/leads; /crm/contacts; /crm/deals;
/crm/lists; /crm/discover; /crm/jobs; /crm/enrich; /crm/inbox; /crm/workflows;
/crm/deliverability; /crm/outbox; /crm/merges; /crm/contactability;
/crm/suppressions; /crm/settings.

Runbook path for crm enroll: open /crm/lists/{id}, Soft Wall preflight, enroll
into Soft Wall sequence; approve on /crm Soft Wall panel if gated.

Jobs history /crm/jobs. Replies and takeover /crm/inbox. Dead-letter retry
/crm/outbox. Kill switches /crm/settings. Sender readiness /crm/deliverability.

Telegram-only is not Must-done; GUI paths are required.

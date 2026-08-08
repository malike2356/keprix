# Agentic CRM compliance (self-knowledge)

UK PECR / GDPR product defaults (not legal advice). Full doc:
docs/features/crm-compliance.md

Suppression always wins at import, materialise, crm enroll, schedule, send, and
handoff. Discovery is not consent. ContactabilityDecision is per person,
channel, purpose (allow / deny / needs_review).

ConsentRecord: lawful_basis, evidence, source, channel, purpose, jurisdiction.

Soft Wall gates: enrich apply, list enroll, customer/paying, merge, kill-switch
resume, subject export.

Operator GUI: /crm/suppressions, /crm/contactability, /crm/deliverability,
/crm/settings, DSAR export on lead/contact detail.

Health pack never stores patient clinical data in CRM discovery lists.

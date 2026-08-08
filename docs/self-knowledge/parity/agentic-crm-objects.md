# Agentic CRM objects (self-knowledge)

Keprix CRM objects (workspace-scoped): Account, Lead, Contact, Deal, Activity,
List, ListMembership, EnrichmentJob, ConsentRecord, SuppressionEntry.

Operator types: DiscoveryJob, OutboxRecord, MergeSuggestion,
ContactabilityDecision, SenderReadiness, KillSwitchState, Provenance,
SourceRecord.

## Stage machine

Forward: discovered -> enriched -> listed -> approved -> enrolled -> contacted
-> engaged -> qualified -> booked -> customer -> paying.

Side/terminal: suppressed, bounced, do_not_contact, lost.

customer and paying need verified business events or Soft Wall-verified deal
outcome. Stripe: do not create new prices.

## Soft Wall gates

Approve discovery list before enrich; enrich fills before write; list before
enroll (crm enroll); first outbound; stage jump to customer/paying; external
scrape; identity merge; kill-switch off; contactability allow when needs_review.

Packages: `src/keprix/crm/`, `sheet_preprocess/`, `discovery/`. Soft Wall lives
in `outreach/` (glue only).

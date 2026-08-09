# Keprix-native standalone lead and outreach contract (v1.0.0)

**Status:** AUTHORITATIVE for series 620-628  
**Contract version:** `1.0.0`  
**Date:** 2026-08-09  
**Machine schema:** `schemas/standalone-lead-outreach/contract.schema.json`

This contract covers Community Edition local single-user and hosted multi-workspace operation. It does **not** require Carina, Aiva, or Propreneur at runtime.

## Identity

| Field | Meaning |
| --- | --- |
| `workspace_id` | Tenant / workspace scope on every durable row and API call |
| `actor_id` | Authenticated user or agent actor; never implicit first-user |
| `correlation_id` | Cross-surface request/job correlation |
| `idempotency_key` | Required for mutations (enroll, send, stage change, merge apply, provider event apply) |

## Entities (reuse CRM names)

Canonical entities: `Account`, `Lead`, `Contact`, `Deal`, `Activity`, `List`, `ListMembership`, `EnrichmentJob`, `ConsentRecord`, `SuppressionEntry`, `DiscoveryJob`, `OutboxRecord`, `Campaign`, `Sequence`, `SequenceStep`, `Enrollment`, `OutboundMessage`, `InboundReply`, `Booking`, `Approval`, `ProviderEvent`, `AttributionRecord`.

Lead fields must cover the SEO lead-tracker compatibility shape (Company, Niche, Town/City, Website, Contact Name, Email, Phone, Google Reviews/Rating/Maps URL, Website Score, Ranks Top3?, Weakness, Priority, Status, Date Added, Notes) plus `source_provenance`, `funnel_stage`, campaign links, delivery history, reply history, and attribution. Synthetic fixtures only in git; never commit private workbooks.

## Lifecycle stages (SoT)

Forward: `discovered → enriched → listed → approved → enrolled → contacted → engaged → qualified → booked → customer → paying`  
Terminal: `suppressed | bounced | do_not_contact | lost`

Outreach pipeline labels map into these stages; they are not a second SoT.

## Lifecycle events

`lead.upserted`, `lead.stage_changed`, `list.enrolled`, `approval.requested`, `approval.resolved`, `message.queued`, `message.sent`, `message.failed`, `provider.bounce`, `provider.complaint`, `provider.delivered`, `reply.ingested`, `booking.offered`, `booking.confirmed`, `suppression.applied`, `merge.applied`.

Every event carries `workspace_id`, `correlation_id`, `occurred_at`, and entity refs.

## Tools (existing names)

Prefer existing agent tools: `crm_*`, `discovery_run`, `sheet_preprocess_*`, `outreach_*`, Companies House search/profile. Extend inputs/outputs; do not rename competing toolsets.

## Soft Wall

High-risk actions reuse existing Soft Wall / approval gates (`apply_enrichment`, `crm.list.enroll`, `stage_customer_paying`, `merge_identity`, outreach send approvals, …). External sends never bypass Soft Wall. Suppressed / opted-out / complained / hard-bounced recipients are never contacted.

## Provider-event normalization

Inbound provider webhooks normalize to:

```json
{
  "provider": "ses|sendgrid|mailgun|smtp|other",
  "event_type": "delivered|bounce|complaint|open|click|rejected",
  "provider_message_id": "string",
  "recipient": "email",
  "occurred_at": "ISO-8601",
  "raw_ref": "opaque storage key",
  "workspace_id": "string",
  "idempotency_key": "string"
}
```

Missing live provider binding is a readiness gap (`MISSING` / `PARTIAL`), not a fake success.

## Error semantics

| Code | When |
| --- | --- |
| `not_configured` | Optional credential missing (CH, Google, ESP) |
| `soft_wall_required` | Mutation needs approval |
| `suppressed` | Recipient blocked |
| `workspace_mismatch` | Cross-tenant attempt |
| `idempotent_replay` | Same key already applied |
| `dry_run` | Send path not live |
| `unsupported_format` | Import format not implemented |

## Persistence modes

- **Local:** workspace-scoped SQLite (`crm.sqlite`, `outreach.sqlite`) remains valid for CE.
- **Hosted:** PostgreSQL where configured; every query enforces `workspace_id`. Prompt 622 closes CRM Postgres migration gaps.

## Compatibility aliases

Existing `/api/crm/*` and `/api/outreach/*` paths remain. New fields are additive. Deprecate dual stage vocabulary by mapping, not by renaming production tables in one jump.

## Readiness

Conformance reports `standalone_outreach_ready: false` until Prompt 628 sign-off. Partial REAL capabilities do not equal programme complete.

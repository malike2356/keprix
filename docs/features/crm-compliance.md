# CRM compliance (consent, suppression, PECR / GDPR controls)

This document describes Keprix CRM defaults for UK cold outreach. It is product
documentation for operators, not legal advice.

## Principles

1. **Suppression always wins** at import, materialisation, enrollment,
   scheduling, send, reply drafting, and channel handoff.
2. **Discovery is not consent.** A Companies House or directory hit does not
   grant contact permission. Contactability and ConsentRecord are separate.
3. **Soft Wall** gates list enroll, customer/paying stage jumps, subject export,
   and kill-switch resume. Do not invent a parallel approval system.

## ConsentRecord

Fields: `lawful_basis` (`legitimate_interest`, `soft_opt_in`, `contract`,
`consent`), `evidence`, `obtained_at` / `captured_at`, `source`,
`channel`, `purpose`, `jurisdiction` (default UK), `assessment_version`.

Create via GUI on contact/lead detail (`Record consent`) or
`POST /api/crm/consents`. Changes write an Activity on the subject timeline.

## SuppressionEntry

Channel address blocks (`email`, `phone`, `telegram`) with `reason`,
`source`, and optional `permanent` flag. Unsubscribe and bounce engagement
ingest create suppressions automatically and stop enrollments.

Manage at `/crm/suppressions`. Undo is Soft Wall gated.

## Contactability

Per person / channel / purpose decisions: `allow`, `deny`, `needs_review`.
Deny surfaces in enroll preflight with a link to `/crm/contactability`.

## Policy decision records

Each send-policy evaluation stores person/entity, purpose, channel,
jurisdiction, policy version, evidence, expiry, and explanation.

## Subject rights runbooks

| Right | Operator path |
| --- | --- |
| Access (export) | Lead/contact detail **DSAR export** (Soft Wall) or `POST /api/crm/leads/{id}/export` |
| Correction | Edit fields on CRM detail; Activity audited |
| Erasure | Soft-delete entity; retain minimal permanent SuppressionEntry addresses |
| Retention | Source records honour `retention_until`; suppressions may be permanent |

## Prohibited targeting

Special-category inference, minors, vulnerable-person targeting,
discriminatory filters, and health/care-recipient lead generation are refused
by `check_prohibited_targeting`.

## Sender readiness

`/crm/deliverability` checklist is a hard gate before first cold campaign Soft
Wall enroll when the snapshot sets `soft_wall_block_cold_send`.

## Defaults (UK)

See `keprix.crm.compliance.UK_DEFAULT_POLICY` (`policy_version`
`uk-crm-defaults-2026.1`). Editable under `/crm/settings` with Soft Wall when
changing live campaign behaviour.

## Channel cookbook (Telegram)

- `/leads find plumbers in Leeds` - queue discovery (Soft Wall before enroll)
- `/leads approve` / `/leads approve <id>` - Soft Wall CRM approvals
- `/leads digest` - funnel digest with `/crm/*` deep links
- `/crm ask <question>` - workspace-scoped CRM ask

Unauthorised / unlinked chats are denied.

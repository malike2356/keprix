# Agentic CRM Nice wave sign-off (P5 / 451-465)

**Date:** 2026-08-08
**Verdict:** READY (all Nice prompts complete; live keys entered by operator in Connections GUI)
**Scope:** Nice-to-haves after Must 429-450. Does not replace Must sign-off (`agentic-crm-signoff.md`).
**Writing style:** plain ASCII only.

## Rule

451 is satisfied by Must visual prompt 508. Do not ship a second canvas runtime.
Operator enters licensed keys/tokens under `/crm/settings#connections` before using live adapters.

## Feature matrix

| Prompt | Title | Status | Notes |
| --- | --- | --- | --- |
| 451 | Visual workflow builder | Complete (via 508) | Visual CRM Must-thin already shipped |
| 452 | Saved ICP versions | Complete | `/crm/icp`, Soft Wall activate, tools |
| 453 | Team assignment + SLA | Complete | Round-robin, locks, comments, `/crm/sla` |
| 454 | CRM integrations | Complete | CSV Soft Wall + adapters; keys via Connections |
| 455 | Template experimentation | Complete | Sticky cohorts, guard pause, Soft Wall promote |
| 456 | Licensed enrichment | Complete | Fake Soft Wall path + Clearbit slot via Connections |
| 457 | Data freshness dashboard | Complete | `/crm/data-quality` |
| 458 | Multilingual campaigns | Complete | Locale Soft Wall publish |
| 459 | WhatsApp / SMS | Complete | Flag + Soft Wall; WA/Twilio keys via Connections |
| 460 | Open/click tracking | Complete | Workspace default off |
| 461 | Social API production | Complete | Health + scrape refuse; social keys/flags via Connections |
| 462 | Voice / call notes | Complete | Activities + retention |
| 463 | Auto ICP scoring / briefs | Complete | Deterministic score + tools |
| 464 | Property portals flagged | Complete | Checklist + kill; portal flag/tokens via Connections |
| 465 | Attribution + Nice cutover | Complete | sourced/influenced/closed |

## Validation

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/pytest tests/crm/test_icp.py tests/crm/test_nice_p5.py tests/crm/test_connections.py -q
```

## Explicit non-goals

- Creating Stripe products or prices
- Unofficial WhatsApp Web / personal account automation
- HTML scrape of LinkedIn / Meta / TikTok / Rightmove / Zoopla by default
- Bundling third-party vendor credentials in the product

## Operator notes

- Configure keys and flags at `/crm/settings#connections` (docs: `docs/features/crm-connections.md`).
- Soft Wall covers ICP activate, paying reassign, imports, experiment promote, locale publish, first WhatsApp/SMS, portal checklist, enrich apply.
- Missing keys return honest `not_configured` / flag-off errors until the operator saves values.

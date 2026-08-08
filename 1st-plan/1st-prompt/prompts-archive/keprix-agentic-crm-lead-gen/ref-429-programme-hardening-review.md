# Ref 429: Programme hardening review and blocker workarounds

**Status: COMPLETED 2026-08-08** (binding requirements applied; programme archived)
**Date:** 2026-08-08
**Writing style:** plain ASCII only.

## Review verdict

The 429-450 sequence is directionally correct, but the first draft describes
features more completely than operating controls. The programme must ship as a
review-first revenue workflow, not an autonomous spam engine. Discovery,
enrichment, identity resolution, consent decisions, sending, reply handling,
and stage changes must remain observable, reversible where possible, scoped to
one workspace, and attributable to a user, agent, source, and policy version.
Must capabilities must also be **viewable and operable from workspace GUI**
(prompt 466); API or Telegram-only paths fail Must sign-off.

This document is binding on every prompt in the series. When a shorter prompt
conflicts with this document, use the safer requirement here unless the owner
explicitly changes it.

## Must-haves

### 1. Workspace, identity, and access safety

1. Every durable row includes `workspace_id`, stable id, created/updated times,
   actor type/id, and version for optimistic concurrency.
2. The store enforces workspace scoping centrally. Callers cannot opt out by
   forgetting a filter. Cross-workspace tests cover list, get, update, delete,
   export, agent tools, background jobs, webhooks, and analytics.
3. Roles separate view, edit, approve, export, connect-source, and send rights.
   Telegram approval requires a linked account, short-lived signed action,
   single use, visible scope, and expiry.
4. Secrets use the existing Keprix provider/vault patterns. They never enter
   CRM rows, prompts, activity bodies, logs, exports, or approval payloads.
5. Bulk destructive changes use preview, count, reason, approval, audit record,
   and a recoverable soft-delete window.

### 2. Provenance and truth

1. Every discovered or enriched field stores field-level provenance: source
   URL or import id, observed time, adapter, evidence excerpt or source field,
   confidence, verification state, and policy version.
2. Distinguish `observed`, `user_supplied`, `derived`, `model_inferred`, and
   `verified`. UI and agent answers must not present inference as fact.
3. The model cannot invent contact details, consent, company registration,
   prices, health information, or protected traits. Unknown stays unknown.
4. Source snapshots are content-hashed and retention-bound. Store the minimum
   evidence needed for review; do not retain entire pages by default.
5. Agent answers cite record ids plus source/evidence ids. Numeric answers run
   against deterministic filters or SQL. The LLM explains results but does not
   calculate hidden totals from sampled text.

### 3. Spreadsheet safety and usability

1. The flow is `upload -> inspect -> map/propose -> validate -> preview diff ->
   approve -> apply -> export or CRM upsert`. Propose never mutates.
2. Enforce file size, row, column, decompression, formula, and processing-time
   limits. Reject encrypted workbooks and macro-enabled content unless an
   explicit safe path exists. Never evaluate spreadsheet formulas.
3. CSV decoding and delimiter detection must be explicit and reviewable.
   Formula-injection characters are escaped on CSV export.
4. Preserve the original file and create a new version. Record a content hash,
   selected worksheet, header row, mapping version, and output hash.
5. Multi-sheet workbooks require sheet selection. Do not silently discard
   other sheets, formulas, charts, hidden rows, or formatting. If preservation
   is unavailable, label the output as a flattened data export before apply.
6. Empty means null or whitespace under a documented policy. Zero, `false`,
   valid formulas, and user-entered placeholders are not automatically empty.
7. User schema supports type, role, units, currency, timezone, allowed values,
   validation, required state, unique key, metric formula, and PII class.
8. Model fills are structured-schema validated, bounded by allowed columns,
   deduplicated, confidence-scored, and accompanied by evidence. Invalid or
   conflicting fills become review issues, not silent skips.
9. Batch retries are idempotent and resumable. Cost and token budgets are
   checked before each batch. Cancellation stops further model calls.
10. The current baseline lives in `src/keprix/sheet_preprocess/`; extend it
    rather than creating another processor.

### 4. Lead identity and data quality

1. Use an identity resolution service, not ad hoc upserts in each adapter.
   Exact keys include workspace plus verified email, company number, source
   external id, or canonical domain. Fuzzy matches are suggestions only.
2. Preserve source-specific records and merge history. A merge must be
   explainable, reversible, and unable to move consent between people.
3. Normalise email, phone, URL, country, postcode, and company names. Validate
   syntax without claiming that a mailbox or person exists.
4. Track completeness, freshness, verification, fit, intent, and engagement as
   separate scores. Never collapse them into one unexplained AI score.
5. Contacts, accounts, leads, and deals have explicit relationships. A company
   lead without a named person is valid and must not trigger guessed contacts.

### 5. Lawful-source and contactability policy

1. Each adapter declares source category, data licence/terms reference,
   allowed fields, permitted purposes, rate limits, geographic scope, retention,
   and whether outreach use is allowed. Health reports this at runtime.
2. Robots directives are not a substitute for permission or contractual rights.
   A source blocked by ToS remains blocked even when technically fetchable.
3. Discovery and contactability are separate decisions. Finding a company does
   not grant permission to contact a person.
4. Consent and legitimate-interest records carry subject type, channel,
   purpose, jurisdiction, evidence, assessment/version, obtained time, expiry,
   and withdrawal. Suppression always wins.
5. No special-category data inference, vulnerable-person targeting, minors,
   discriminatory targeting, or automated consequential decisions.
6. Health and social care packs target organisations and professional contacts
   only by default. Patient, referral, or care-recipient data is out of scope
   for lead generation.
7. Compliance rules are policy engine inputs, not hard-coded UK-only booleans.
   UK defaults are conservative. Expansion to another jurisdiction requires a
   reviewed policy pack.

### 6. Outreach safety and deliverability

1. Before first send, require campaign purpose, audience, lawful-basis result,
   sender identity, physical/contact address where required, unsubscribe path,
   template preview, sample recipients, schedule, caps, and approval.
2. Separate campaign approval from execution approval. Material edits to
   audience, template, sender, channel, cadence, or link targets invalidate the
   prior approval.
3. Enforce workspace, campaign, domain, and contact rate caps; quiet hours;
   timezone-aware scheduling; randomised safe windows; and global kill switch.
4. Check suppression at list materialisation, enrollment, scheduling, and
   immediately before send. The final check is mandatory to close race windows.
5. Use idempotency keys per campaign, recipient, channel, and step. Retries
   cannot double-send. Use a transactional outbox and dead-letter queue.
6. Domain readiness is a hard gate: verified sender, SPF, DKIM, DMARC guidance,
   reply mailbox, webhook signature verification, bounce handling, and gradual
   warm-up. Do not promise inbox placement.
7. Track delivery, transient bounce, hard bounce, complaint, reply,
   unsubscribe, and provider rejection. Opens and clicks are optional and
   privacy-sensitive, not reliable truth signals.
8. Hard bounce, complaint, unsubscribe, legal threat, negative reply, or human
   takeover stops automation immediately. A normal reply pauses sequence until
   classified or handled.
9. Content generation uses approved claims and source facts. It cannot fabricate
   testimonials, relationships, urgency, pricing, accreditations, or personal
   familiarity.

### 7. Replies, nurture, and human ownership

1. Store raw inbound event id and immutable metadata, then a separate mutable
   classification with model/version/confidence. Webhook replay is idempotent.
2. Reply classes include interested, question, referral, objection,
   not_interested, unsubscribe, complaint, out_of_office, auto_reply, bounce,
   wrong_person, and human_review.
3. Low confidence, ambiguous requests, negotiation, regulated advice, complaint,
   or legal language goes to a named human queue with SLA and escalation.
4. Agent-drafted replies are previews by default. Autonomous replies require a
   narrow approved policy, confidence threshold, approved knowledge, and daily
   cap. Never auto-send contractual, medical, legal, pricing-discretion, or
   reputationally sensitive answers.
5. Stage suggestions and communication state are separate. A reply may pause a
   sequence without promoting a deal. `customer` and `paying` require verified
   business events, not model sentiment.
6. Workflows have entry conditions, stop conditions, ownership, version,
   activation window, maximum duration, maximum touches, and re-enrollment rule.
7. All scheduled work is visible and cancellable. Human takeover displays who
   owns the next action and prevents agent sends until explicitly released.

### 8. Operations, observability, and economics

1. Durable jobs expose queued, running, awaiting_approval, paused, succeeded,
   partially_succeeded, failed, cancelled, and dead_letter states.
2. Record attempts, cursor, checkpoint, error category, next retry, cost, and
   correlation id. Operators can retry safe units without repeating completed
   external actions.
3. Audit every agent read/write of sensitive CRM data, every external fetch,
   approval, send, stage transition, export, merge, suppression change, and
   policy decision. Logs redact content and PII by default.
4. Per-workspace budgets cover discovery fetches, enrichment tokens, emails,
   and concurrent jobs. Forecast cost before approval and stop at hard limits.
5. Provide kill switches per adapter, campaign, workspace, channel, and system.
   Pausing prevents new sends while preserving state for investigation.
6. Backups, retention deletion, subject access export, correction, erasure, and
   suppression retention have tested runbooks.
7. Success metrics include valid contact rate, approval yield, deliverability,
   positive reply rate, booked rate, qualified pipeline, revenue, cost per
   qualified opportunity, unsubscribe, complaint, and false-enrichment rate.
   Vanity counts alone are insufficient.

## Nice-to-haves

1. Saved ICP definitions with versioned inclusion and exclusion criteria.
2. Evidence-backed account briefs and suggested personalisation angles.
3. Visual workflow builder that compiles to the same versioned workflow model.
4. Team assignment, round-robin ownership, SLA inbox, collision detection, and
   comments/mentions.
5. Data-quality dashboard for stale, conflicting, unverified, and incomplete
   fields, with scheduled re-verification.
6. Template experiments with fixed cohorts, minimum sample warnings, and guard
   metrics for complaints and unsubscribes.
7. Bring-your-own licensed enrichment providers through the adapter contract.
8. HubSpot, Salesforce, Pipedrive, and GHL import/export with external-id maps
   and conflict previews.
9. WhatsApp Business and SMS only through official providers, explicit channel
   consent, template approval, and jurisdiction policies.
10. Multilingual templates with human review and locale-specific compliance.
11. Call notes and voice-note transcription with consent and retention controls.
12. Attribution models that distinguish sourced, influenced, and closed revenue.

## Not a must-have

1. Open pixels and click wrappers. Privacy and bot traffic make them secondary.
2. Predictive ML scoring before enough labelled conversion data exists.
3. Unofficial social or portal scraping.
4. Fully autonomous negotiation or closing.
5. Every channel in v1. Reliable email plus operator Telegram is the right
   first operational slice.

## Blockers and practical workarounds

| Blocker | Safe workaround | Degraded behaviour to show |
| --- | --- | --- |
| Social API access unavailable | Import platform exports, lead-ad webhooks, user-provided lists, or licensed provider data | Adapter health says `not_configured`; no pretend results |
| Portal scraping prohibited | User CSV, licensed feed, saved-search email import, Companies House, or general web results allowed by source terms | Portal adapter remains disabled |
| No public API for a directory | Manual upload, documented browser-assisted user action, or partnership/licence | Do not automate prohibited collection |
| Contact email unavailable | Keep account lead, use public contact form only with approval, request referral, or research a published role mailbox | Never guess an address |
| Phone outreach consent unclear | Disable automated calling/SMS; create a human research task | Channel marked ineligible |
| LLM unavailable or budget exhausted | Heuristic column mapping, validation, dedupe, and review still work; queue optional enrichment | Job becomes `partially_succeeded` |
| Model confidence low | Leave cell blank and create review issue | Unknown remains visible |
| Workbook cannot be safely preserved | Produce an explicit flattened CSV/XLSX data export plus original file | Warn before approval |
| Sender domain not ready | Draft and approve campaign, but block send until SPF/DKIM/DMARC and mailbox checks pass | Campaign status `blocked_sender_readiness` |
| Reply webhook unavailable | Signed provider polling or IMAP fallback with UID state and dedupe | Display ingestion latency |
| Telegram account not linked | Read-only generic guidance; require web login to link | No CRM content or approval buttons |
| Jurisdiction cannot be determined | Apply the strictest configured policy and require human review | Contact remains non-contactable |
| Ambiguous duplicate | Create merge suggestion, preserve both records, block double enrollment | Human resolves identity |
| Provider outage or rate limit | Exponential backoff with jitter, checkpoint cursor, circuit breaker, and operator-visible retry | No duplicate fetch or send |
| Existing Soft Wall schema cannot express a gate | Add typed approval payload/version through its extension point; do not create a parallel approval system | Feature stays gated until supported |
| Existing contacts and CRM disagree | Establish CRM relationship mapping and conflict UI; do not overwrite either store silently | Migration report lists conflicts |
| Revenue event unavailable | Allow manually verified deal outcome with actor/evidence; add external billing ids later | Do not infer `paying` from replies |

## Revised delivery slices

### Slice A: safe data foundation

Prompts 429-435 plus identity resolution, provenance, policy decisions, file
limits, deterministic ask-data, and isolation. Exit criterion: a sheet can be
proposed, reviewed, applied, and queried without external sending.

### Slice B: compliant list building

Prompts 436-441 plus adapter manifests, source permissions, checkpoints,
dedupe/merge suggestions, and contactability decisions. Exit criterion: a
reviewed list has source evidence and an explicit send eligibility result.

### Slice C: controlled email outreach

Prompts 442-448 plus sender readiness, transactional outbox, idempotency,
final suppression check, reply pause, human queue, and kill switches. Exit
criterion: a small approved test campaign can run without duplicate sends.

### Slice D: channel operation, GUI, and scale

Prompts 445-450 plus **466 operator console**, Telegram signed approvals,
analytics, runbooks, retention, load tests, failure drills, and staged rollout.
Exit criterion: operator sign-off uses real evidence from a non-production
workspace and a limited pilot; every Must capability has a GUI path.

## Final sign-off additions

Prompt 450 must fail readiness unless all are demonstrated:

- cross-workspace denial across HTTP, tools, jobs, exports, and analytics;
- no mutation before enrichment approval;
- no overwrite of non-empty cells;
- no send without eligibility, approval, sender readiness, and final suppression check;
- retry does not duplicate a lead, enrollment, message, reply, or booking;
- reply, unsubscribe, complaint, bounce, kill switch, and human takeover stop sends;
- provenance is visible for discovered and enriched fields;
- LLM outage leaves a usable non-AI path;
- source/API blocker produces an honest degraded state;
- retention, export, correction, deletion, and suppression runbooks pass;
- staged pilot has explicit caps and rollback criteria;
- operator can complete discover -> Soft Wall list -> enroll -> reply inbox from GUI without curl;
- jobs, outbox/dead-letter, merges, contactability, deliverability, and kill switches are viewable under `/crm/*`.

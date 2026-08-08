# Agent brief: Prompt 111 Scout evidence pack and clinical event taxonomy

**Status:** Archived in `prompts-archive/111-scout-evidence-pack-and-clinical-event-taxonomy.md`  
**Verification closed:** 2026-07-12 (automated gaps closed; smoke tests green).
**Reconciled:** 2026-07-05 (checklist vs code/tests)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`  
**Goal:** Implement signed clinical event taxonomy, local audit + Scout queue dispatch, and verifiable evidence pack zip generation with optional Scout upload.

**MVP:** Shipped. Core modules, routes, governance UI, and 5 tests in `tests/scout/test_clinical_events.py` (covers evidence pack generation; no separate `tests/evidence_pack/` tree).

**Prerequisites:**

- Archived Prompt 38 (`src/keprix/scout/`: enrollment, heartbeat, `event_reporter`, signing, policy receiver)
- Archived Prompt 107 review gateway (emit review lifecycle events)
- Archived Prompt 109 GDPR, Prompt 110 legal gate (events listed in taxonomy)
- [113-outbound-notify-external-verification.md](./113-outbound-notify-external-verification.md) for `evidence_pack_ready` email (optional at archive time)
- [112-clinical-pack-gate-verification.md](./112-clinical-pack-gate-verification.md) should wire `emit_clinical_event` on approve/reject/rollback

---

## Context

Generic Scout events exist via `scout/event_reporter.py` (`queue_audit_event`). Prompt 111 adds:

1. **`CLINICAL_EVENT_TYPES`** registry with strict validation
2. **`ClinicalEvent`** envelope with HMAC signature
3. **`emit_clinical_event()`** helper (audit log + Scout queue)
4. **Evidence pack** zip: manifest, per-event JSON, audit CSV, optional PDFs, `VERIFY.txt`
5. **Scout upload** `POST /api/v1/evidence-packs`

Pack gate uses `emit_clinical_event` from `scout/clinical_events.py` (wired in `pack_gate/service.py`).

---

## File layout (create)

```text
src/keprix/scout/clinical_events.py   # CLINICAL_EVENT_TYPES, ClinicalEvent, emit_clinical_event, sign_event
src/keprix/scout/clinical_schemas.py  # optional: per-event detail TypedDicts / Pydantic models

src/keprix/evidence_pack/
  __init__.py
  generator.py        # generate_evidence_pack, build_evidence_zip
  manifest.py         # manifest.json + manifest_signature
  collector.py        # collect_clinical_events, collect_linked_documents
  store.py            # pack metadata + file_store path
  routes.py             # /api/evidence-pack/*

tests/scout/test_clinical_events.py   # includes evidence pack generator/manifest tests

frontend/src/app/(workspace)/settings/governance/evidence-packs/page.tsx
frontend/src/lib/evidence-pack-api.ts
```

Wire `evidence_pack.routes` in `api/server.py`.

---

## Clinical events implementation

### `clinical_events.py`

| Task | Detail |
| --- | --- |
| Taxonomy | `CLINICAL_EVENT_TYPES` dict exactly as in prompt (hazard, review, scan, evidence, GDPR, legal) |
| Validation | Unknown `event_type` raises `ValueError`; never silently queue |
| Signing | HMAC-SHA256 over canonical JSON (sorted keys, `signature` omitted); secret from vault key `CLINICAL_EVENT_HMAC_SECRET` |
| Local audit | Write to existing audit log (`src/keprix/security/` or audit module used by Prompt 02) |
| Scout queue | If `scout_config.enabled`, enqueue via `scout/store.py` with full signed payload |
| Public API | `async def emit_clinical_event(...) -> str` returns `event_id` |

### Call sites to wire (minimum)

| Module | Events |
| --- | --- |
| `review_gateway/` | `cso_review_assigned`, `cso_review_approved`, `cso_review_rejected`, `cso_review_expired`, reminders |
| `pack_gate/service.py` | approve/reject/rollback events per prompt 112 |
| `privacy/` (109) | `gdpr_*` events |
| `legal/` (110) | `legal_acceptance_recorded`, `legal_policy_published` |
| `evidence_pack/generator.py` | `evidence_pack_generated`, `evidence_pack_exported` |

Use `reviewer_email_hash` (sha256) in detail payloads; never store raw reviewer email in event detail.

---

## Evidence pack implementation

### Zip layout

```text
evidence-pack-{pack_id}/
  manifest.json
  events/{event_id}.json
  documents/{filename}.pdf
  audit_extract.csv
  VERIFY.txt
```

### `manifest.json`

Fields and `manifest_signature` per prompt. `events_sha256` and `documents_sha256` maps must match actual file hashes in zip.

### Generator flow

1. `collect_clinical_events(workspace_id, date_from, date_to, event_types?, domain_pack?)`
2. Optional linked PDFs from export store (Prompt 108 `ExportStore`)
3. `audit_log.export_csv(...)` for period
4. Build zip in memory; save to workspace file store `evidence-packs/{pack_id}.zip`
5. `emit_clinical_event("evidence_pack_generated", ...)`

### API routes

- `POST /api/evidence-pack/generate`
- `GET /api/evidence-pack` (list)
- `GET /api/evidence-pack/{pack_id}`
- `GET /api/evidence-pack/{pack_id}/download`
- `POST /api/evidence-pack/{pack_id}/send-to-scout`

`send-to-scout`: HTTP 409 when Scout disabled; otherwise POST zip to `{scout_url}/api/v1/evidence-packs` with headers from prompt; store `scout_submission_id`.

### Verification helper (tests)

Provide `verify_event_signature(event_dict, secret)` and `verify_manifest(manifest_dict, zip_bytes, secret)` for unit tests.

---

## UI (minimal)

Governance or settings page:

- Date range picker, event type multi-select, domain pack filter
- Generate button; list prior packs with status, event count, download link
- Send to Scout button (disabled with message when Scout not connected)

Can extend existing `frontend/src/app/(workspace)/settings/governance/` if present.

---

## Verification commands

```bash
cd /opt/lampp/htdocs/verlox/keprix

PYTHONPATH=src .venv/bin/python -m pytest tests/scout/test_clinical_events.py -q

# Scout bridge regression
PYTHONPATH=src .venv/bin/python -m pytest tests/scout/ -q

# Downstream emitters after wiring
PYTHONPATH=src .venv/bin/python -m pytest tests/pack_gate/ tests/review_gateway/ tests/legal/ tests/privacy/ -q

cd frontend && pnpm build
```

Manual:

1. Emit test clinical event; confirm audit log row + Scout queue row (Scout enabled)
2. Generate pack for 7-day window with known events; unzip; verify  manifest hashes
3. Tamper one event file; signature verification fails
4. `send-to-scout` with Scout disabled returns 409

---

## Acceptance checklist (from Prompt 111)

- [x] Valid `event_type` writes audit log and queues to Scout when enabled (`clinical_events.py`; `test_emit_clinical_event_signs_and_stores`)
- [x] Invalid `event_type` raises `ValueError` (`test_invalid_event_type_raises`)
- [x] Each event JSON in zip has verifiable HMAC signature (`sign_event` / `verify_event_signature`; events signed before zip assembly)
- [x] `manifest.json` sha256 entries match files in zip (`test_evidence_pack_zip_manifest_hashes_match`)
- [x] `manifest_signature` verifies correctly (`verify_manifest_signature` in same test)
- [x] Pack with 20 events produces exactly 20 event JSON files (`tests/governance/test_evidence_pack_gaps.py`)
- [x] `send-to-provider` returns 409 when provider not configured (route wired on `server.py`; gap tests)
- [x] `send-to-provider` with provider connected returns submission ID (mocked httpx in gap tests)
- [x] GDPR and legal events appear when filters include those types (`test_generate_evidence_pack_counts_events` uses `gdpr_dsar_requested`; collector filters by `event_types`)
- [x] `GET /api/evidence-pack` lists packs with status and event counts (`test_list_evidence_packs_route`)

### Hardening closed (2026-07-12)

1. Route tests for list/download/send-to-provider (409 + mocked success).
2. Generator test that asserts N events produce N JSON files in the zip.
3. Evidence pack router registered on `src/keprix/api/server.py`.

---

## Out of scope

- Labyrinth Scout console changes (ingest side assumed available)
- Hazard log COMPASS domain pack (future domain pack work)
- Prompt 113 delivery of pack download links to external auditors (template exists after 113)

---

## Archive when done

1. All acceptance items checked
2. `pack_gate` and `review_gateway` use `emit_clinical_event`, not raw `queue_audit_event`
3. `tests/scout/test_clinical_events.py` green (evidence pack coverage lives here)
4. Move prompt to `planning/prompts/prompts-archive/111-scout-evidence-pack-and-clinical-event-taxonomy.md`
5. Update `pending-prompts/PROMPT-IMPLEMENTATION-AUDIT.md`

---

## Suggested execution order (this cluster)

```text
113 notify_external  -->  112 pack gate (finish + wire email/events)
                        -->  111 clinical taxonomy + evidence packs
```

Brief **112** can land incrementally before **111**, but do not archive **112** until **113** email and **111** clinical emits are wired.

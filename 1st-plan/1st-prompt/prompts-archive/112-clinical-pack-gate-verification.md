# Agent brief: Prompt 112 clinical pack gate

**Status:** Archived in `prompts-archive/112-clinical-pack-gate.md`  
**Verification closed:** 2026-07-12 (automated gaps closed; smoke tests green).
**Reconciled:** 2026-07-05 (checklist vs code/tests)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`  
**Goal:** Finish the regulated pack sign-off gate so install/activate separation, approver workflow, rollback, and notifications meet Prompt 112 acceptance criteria.

**MVP:** Shipped. 7 tests pass in `tests/pack_gate/`. Dependencies 111 and 113 are wired in production paths.

**Prerequisite:** Complete [113-outbound-notify-external.md](./113-outbound-notify-external.md) first (approver email).  
**Follow-up:** Complete [111-scout-evidence-pack-verification.md](./111-scout-evidence-pack-verification.md) to replace `_emit_clinical_event` stub with signed taxonomy events.

---

## Context

Pack gate sits between hub pack install and runtime activation for safety-sensitive workspaces (DCB0160 / IEC 62304 change control). Gate is off by default; when enabled, packs install but stay inactive until an approver signs off.

**Foundation already shipped** (do not rebuild):

| Area | Path |
| --- | --- |
| Store + models | `src/keprix/pack_gate/store.py`, `models.py`, `schemas.py` |
| Gate logic | `src/keprix/pack_gate/gate.py` (`validate_manifest_changelog`, `activate_pack`, `PackGateRequired`) |
| Service | `src/keprix/pack_gate/service.py` (`after_pack_install`, `approve_record`, `reject_record`, `rollback_pack_version`) |
| API | `src/keprix/pack_gate/routes.py` (wired in `api/server.py`) |
| Hub hook | `src/keprix/hub/routes.py` (202 on gated install, changelog 422) |
| Inbox stub | `src/keprix/pack_gate/notifications.py` (jsonl inbox + email log) |
| UI | `frontend/src/app/(workspace)/settings/pack-gate/page.tsx` |
| Sign-off UI | `frontend/src/app/(workspace)/packs/[pack_id]/gate/page.tsx` |
| API client | `frontend/src/lib/pack-gate-api.ts` |
| Tests | `tests/pack_gate/test_gate.py` (3), `tests/pack_gate/test_routes.py` (4) |

**7 tests pass.** Rollback API path and non-approver 403 are the main test gaps.

---

## Implementation notes (done)

- **Email (113):** `pack_gate/notifications.py` calls `notify_external.smtp_sender.send_email` with `pack_gate_pending`; inbox alert via `get_inbox_service()`.
- **Clinical events (111):** `pack_gate/service.py` uses `emit_clinical_event` on approve (`pack_gate_approved`), reject (`pack_gate_rejected`), and rollback (`compliance_finding_raised`).
- **Sign-off UI:** `packs/[pack_id]/gate/page.tsx` disables actions for non-approvers; API returns 403 via `PermissionError` in routes.
- **History:** `GET /api/pack-gate/packs/{pack_id}/history` and settings UI `RecordsTable` for pending + recent history.

---

## Remaining gaps (optional hardening)

1. Add rollback route test: prior version active, `pack_gate_rollback_log` row, clinical event emitted.
2. Add non-approver `approve`/`reject` returns 403 test.
3. Add notification test with `notify_on_install=True` (inbox + mocked SMTP).

---

## Verification commands

```bash
cd /opt/lampp/htdocs/verlox/keprix

PYTHONPATH=src .venv/bin/python -m pytest tests/pack_gate/ -q

# Hub + gate integration
PYTHONPATH=src .venv/bin/python -m pytest tests/hub/ -q -k install

cd frontend && pnpm build
```

Manual:

1. Enable gate in `/settings/pack-gate`; set approver
2. Install pack from `/hub`; expect HTTP 202, pack disabled
3. Open sign-off page; approve; pack enabled
4. Roll back; prior version active; history shows rollback entry

---

## Acceptance checklist (from Prompt 112)

- [x] Gate enabled: install sets `installed` not active; response includes `gate_required: true` (`test_install_returns_202_when_gate_enabled`)
- [x] Approver receives workspace inbox notification on pending install (`notify_pack_pending_approval` + inbox service; not isolated in tests)
- [x] Approver receives email via notify_external (`notifications.py` -> `send_email`; not isolated in tests)
- [x] Sign-off page shows changelog from manifest (`packs/[pack_id]/gate/page.tsx`)
- [x] Approve sets `approved` and activates pack (`test_approve_activates_pack`)
- [x] Reject sets `rejected`; pack stays inactive (`test_reject_leaves_pack_disabled`)
- [x] Non-approver sees page but cannot submit (UI read-only + API 403 in `routes.py`; no 403 test)
- [x] Rollback activates prior approved version in one step (`test_rollback_activates_prior_approved_version`)
- [x] Rollback logged to `pack_gate_rollback_log` + clinical event (`append_rollback_log` + `emit_clinical_event`; covered by rollback test)
- [x] Missing changelog returns HTTP 422 when `require_changelog=true` (`test_missing_changelog_rejected_with_422`)
- [x] Gate disabled: immediate activation unchanged (`test_gate_disabled_allows_immediate_activation`)
- [x] History UI shows records with correct status and timestamps (`settings/pack-gate/page.tsx` RecordsTable)

---

## Out of scope

- Evidence pack generation (Prompt 111)
- Full Prompt 24 notification center UI
- Postgres migrations if JSONL store is sufficient for local/dev (match existing `pack_gate/store.py` pattern; add Alembic only if project convention requires)

---

## Archive when done

1. All acceptance items checked (including 113 and 111 dependencies)
2. `tests/pack_gate/` covers approve, reject, rollback, 422 changelog, 202 install
3. No production email jsonl stub in `pack_gate/notifications.py`
4. Move prompt to `planning/prompts/prompts-archive/112-clinical-pack-gate.md`
5. Update `pending-prompts/PROMPT-IMPLEMENTATION-AUDIT.md`

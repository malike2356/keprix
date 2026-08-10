# AI transparency, consent, and generation log (SGI)

Keprix implements EU AI Act transparency controls for synthetically generated
information (SGI): visible labeling, an append-only generation log, and
granular consent before user input reaches a model.

## Package

`src/keprix/transparency/`

| Piece | Role |
| --- | --- |
| `labels.py` | SGI disclosure for text/code/image/audio/video (en/fr/de/es) |
| `generation_log.py` | Append-only log of SHA-256 input/output hashes |
| `consent_gate.py` | Affirmative, per-feature, withdrawable consent |
| `pipeline.py` | `prepare_ai_call` + `finalize_ai_output` middleware helpers |
| `routes.py` | `/api/transparency/*` |
| `AGENTS.md` | Hard rules for agent/runtime authors |

Postgres migration `038_ai_transparency_generation_log` creates `generation_log`
and `REVOKE`s `UPDATE`/`DELETE` from `keprix` and `app_user` when those roles exist.
SQLite fallback under the data dir remains append-only in application code.

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `KEPRIX_AI_CONSENT_REQUIRED` | `true` | Block AI calls without feature consent |
| `KEPRIX_AI_LABELING_ENABLED` | `true` | Attach disclosure metadata/labels |
| `KEPRIX_AI_GENERATION_LOG_ENABLED` | `true` | Write generation log entries |

## Operator flow

1. Open Privacy in the workspace.
2. Affirmatively check consent for each AI feature (for example `text_generation`).
3. Chat and other AI surfaces then proceed; assistant messages show a
   non-dismissible "AI-generated content" disclosure.
4. Export a day report: `GET /api/transparency/compliance-report?date=YYYY-MM-DD`.

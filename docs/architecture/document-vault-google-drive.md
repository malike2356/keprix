# Document Vault Google Drive sync (Prompt 649)

**Status:** REAL (server push + local poll share one reconciler)  
**Date:** 2026-08-09

## Behaviour

- Local Community Edition vault works with Google disabled (`KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC` default off).
- Encrypted per-workspace OAuth grants (Fernet); tokens never appear in status JSON.
- Modes: `outbound_only` (`drive.file`), `inbound_only` / `two_way` (full Drive) with consent copy.
- One reconciliation engine handles webhook wakeups and manual/poll sync via saved `changes.list` page tokens.
- Conflicts preserve both versions (`both_preserved`); resolve with `keep_local` | `keep_remote` | `keep_both`.
- HTTPS push notifications renew before expiry with overlap; local installs without HTTPS use poll/manual.
- Shared Drives remain gated (`KEPRIX_DOCUMENT_VAULT_GOOGLE_SHARED_DRIVES` forced false).

## HTTP

Prefix: `/api/document-vault/google/`

| Route | Role |
| --- | --- |
| `GET /status` | Public connection status (no secrets) |
| `POST /connect` | Begin OAuth with mode scopes |
| `POST /callback` | Store exchanged tokens (encrypted) |
| `POST /configure` | Root folder + mode |
| `POST /sync` | Inbound reconcile or outbound push |
| `GET /conflicts` | List conflict mappings |
| `POST /conflicts/{id}/resolve` | Resolve conflict |
| `POST /disconnect` | Stop watch + drop grant |
| `POST /watch/renew` | Renew notification channel |
| `POST /refresh` | Refresh access token |
| `POST /webhook` | Google change wakeup (channel token verified) |

## Flags

- `KEPRIX_DOCUMENT_VAULT_ENABLED`
- `KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC`
- `KEPRIX_DOCUMENT_VAULT_GOOGLE_WEBHOOK_URL` (must be `https://...` for push)
- `KEPRIX_DOCUMENT_VAULT_GOOGLE_TOKEN_KEY` (or vault/secret key)

## Tests

```bash
./.venv/bin/python -m pytest tests/document_vault/test_google_drive_sync.py -q
```

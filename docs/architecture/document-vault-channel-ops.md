# Document Vault channel and Telegram ops (Prompt 651)

Trusted channel identity bindings map `(platform, channel_user_id)` to a workspace. Unbound, revoked, public, and anonymous identities get no vault access. Workspace is never inferred from message content, filenames, or model arguments.

## Surfaces

| Piece | Path |
| --- | --- |
| Package | `src/keprix/document_vault/channel/` |
| Gateway helper | `src/keprix/gateway/vault/` |
| Slash | `/vault` in `keprix.slash.builtins` |
| HTTP | `POST /api/document-vault/channel/bindings`, `GET /api/document-vault/delivery/{token}` |
| Alembic | `031_document_vault_channel_ops` |

## Workflows

- Discoverable: `/vault status|list|search|mkdir|create|rename|move|update|export|sync|import|bind|revoke`
- Inbound files: quarantine (MIME sniff, size, macros, AV hook) then canonical `import_bytes` with event-id dedup
- Ambiguous destination: require `parent_id` when root has multiple folders
- Export: channel attachment when under platform size and classification limits; otherwise short-lived single-use URL
- Soft Wall: classified channel export still requires approval (650)

## Channel matrix

Telegram, Slack, Teams, WhatsApp, Discord, email, and web support files. SMS does not.

## Flags

`KEPRIX_DOCUMENT_VAULT_ENABLED` must be on. `KEPRIX_DOCUMENT_VAULT_CHANNEL_OPS` defaults to follow enabled.

## Tests

```bash
./.venv/bin/python -m pytest tests/document_vault/test_channel_ops.py -q
```

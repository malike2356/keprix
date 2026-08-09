# Document Vault agent tools and Soft Wall (Prompt 650)

Trusted session context supplies workspace and actor. Model-supplied tenants and host paths fail closed (`workspace_mismatch`, `host_fs_forbidden`).

## Toolset

`document_vault_*` in `src/keprix/tools/document_vault_tools.py` (toolset `document_vault`):

- Browse: `list`, `search`, `inspect`, `read` (ranged), `revisions`
- Mutate: `create_folder`, `create_file`, `update`, `append`, `rename`, `move`, `copy`, `trash`, `restore`, `restore_revision`, `import`, `export`
- Sync: `sync_status`, `sync_request`, `conflict_resolve`
- High-impact: `permanent_delete`, `bulk`, `share` (Soft Wall)

Flags: tools require `KEPRIX_DOCUMENT_VAULT_ENABLED=1` (default off until Prompt 653 ready flip).

## Soft Wall (Rule of Two)

Gates via CRM Soft Wall (`keprix.document_vault.soft_wall`):

| Kind | When |
| --- | --- |
| `document_vault.permanent_delete` | Permanent delete of trashed item |
| `document_vault.external_share` | External share grant |
| `document_vault.permission_change` | Permission changes |
| `document_vault.bulk_destructive` | Bulk trash / permanent delete |
| `document_vault.conflict_overwrite` | Keep-remote / keep-local overwrite |
| `document_vault.classified_export` | Export of secret/restricted/confidential |

Resume with `approval_id` after operator approve. Approval deep links land on `/documents?item=...&approval=...`.

## Legacy tools

- Markdown knowledge `vault_read` / `vault_write` / `vault_search` redirect or fail with `migrated` when Document Vault is enabled.
- Host `file_tools` remain host/project FS only; never tenant Document Vault IDs.

## Tests

```bash
./.venv/bin/python -m pytest tests/document_vault/test_agent_tools_policy.py -q
```

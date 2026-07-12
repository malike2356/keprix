# Knowledge vault

Prompt **259** adds a universal markdown vault provider. This is separate from
the encrypted credential vault: the knowledge vault points Keprix at a markdown
folder such as Obsidian, Logseq, Foam, or a plain directory.

## Configure

Set `KEPRIX_VAULT_ROOT` for CLI sessions, or use `/settings/vault`.

```yaml
vault:
  provider: local_folder
  root_path: ~/.keprix/workspaces/knowledge-hub
  watch: true
```

## API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/vault/config` | Current knowledge-vault config |
| PUT | `/api/vault/config` | Set provider and root folder |
| GET | `/api/vault/files` | List files |
| GET | `/api/vault/files/{path}` | Read a markdown file |
| PUT | `/api/vault/files/{path}` | Write a markdown file |
| GET | `/api/vault/search?query=...` | Search markdown files and wiki-links |
| GET | `/api/vault/graph` | Return nodes and wiki-link edges |

UI: `/memory/galaxy` (Memory Galaxy). Click a node to open the note; toggle Circle or Force layout. Configure the root at `/settings/vault`.

## Behavior

- `LocalFolderVault` works with any markdown folder.
- `ObsidianVault` is a compatibility wrapper over the local folder provider.
- Writes preserve existing YAML frontmatter when replacing the body.
- Wiki-links like `[[page]]` power backlinks, search, and graph edges.
- Structured workspaces from prompt **258** can be used as vault roots.
- Prompt **270**: web conversations auto-capture into `conversations/` (see [Vault auto-capture](vault-auto-capture.md)). If unset, Keprix creates `~/.keprix/vault`.

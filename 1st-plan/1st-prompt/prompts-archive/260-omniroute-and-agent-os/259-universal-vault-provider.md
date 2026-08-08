# Keprix - Prompt 259: Universal Vault Provider

**Series:** Agentic OS adoption **256-265**  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Supersedes draft:** `248-universal-vault-provider.md`  
**Depends on:** **258** (recommended)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**VaultProvider** abstraction: any markdown folder is the agent knowledge base (Obsidian, Logseq, Foam, plain folder). Two-way read/write with frontmatter merge and graph/backlink support.

**Non-goals:** Obsidian desktop plugin; Trilium/Logseq-specific servers beyond `LocalFolderVault` v1.

---

## 2. Already built

| Area | Location |
| --- | --- |
| Obsidian reader | `research_workspace/obsidian.py` |
| Obsidian routes | `research_workspace/obsidian_routes.py` |
| Documents API | `workspace/routes/document_routes.py` |
| RAG | `memory/rag/` |

Refactor Obsidian-specific paths to use `VaultProvider` internally where practical without breaking existing routes.

---

## 3. Interface

```python
class VaultProvider(ABC):
    async def list_files(self, path: str = "/") -> list[VaultFile]: ...
    async def read_file(self, path: str) -> str: ...
    async def write_file(self, path: str, content: str) -> None: ...
    async def delete_file(self, path: str) -> None: ...
    async def search(self, query: str) -> list[VaultFile]: ...
    async def get_backlinks(self, path: str) -> list[str]: ...
    async def get_graph(self) -> dict: ...
```

Implementations v1:

- `LocalFolderVault` (required)
- `ObsidianVault` (thin wrapper, default)

---

## 4. Configuration

```yaml
# config.yaml
vault:
  provider: local_folder
  root_path: ~/.keprix/workspaces/knowledge-hub
  watch: true
```

Env bridge: `KEPRIX_VAULT_ROOT` for CLI.

Settings UI: **Settings > Vault** path picker + test connection.

---

## 5. API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/vault/config` | Current vault |
| PUT | `/api/vault/config` | Set root |
| GET | `/api/vault/files` | List tree |
| GET | `/api/vault/files/{path}` | Read |
| PUT | `/api/vault/files/{path}` | Write |
| GET | `/api/vault/search` | Full-text |
| GET | `/api/vault/graph` | Nodes + edges |

Agent tools (service-gated): `vault_read`, `vault_write`, `vault_search` registered via skill or gated tools when vault configured.

---

## 6. Sync with **258**

When vault root equals a structured workspace from **258**, index generator hooks remain authoritative for `index.md`; vault writes must not delete indexes.

---

## 7. Files to create

```
src/keprix/vault/
  __init__.py
  provider.py
  local_folder.py
  obsidian_adapter.py
  config.py

src/keprix/api/vault_routes.py

src/keprix/tools/vault_tools.py   # gated tools

frontend/src/app/(workspace)/settings/vault/page.tsx

docs/features/vault.md

tests/vault/
  test_local_folder_vault.py
  test_vault_routes.py
  test_vault_tools.py
```

---

## 8. Acceptance criteria

- Point vault at external folder; list/read/write roundtrip works.
- Wiki-links `[[page]]` resolve in search and backlinks.
- Graph endpoint returns nodes for all `.md` files and edges for links.
- Existing Obsidian research routes keep working (adapter or compat shim).
- Write preserves YAML frontmatter when updating body.
- Tests use temp directories only.

---

## 9. Dependencies

- **258** templates optional but documented as recommended layout

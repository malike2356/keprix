# keprix - Prompt: Universal Vault Provider (Any Markdown Folder as Agent Knowledge Base)

## Purpose

keprix already reads Obsidian vaults (`research_workspace/obsidian.py`, Prompt 75). But the integration is Obsidian-specific. The user's knowledge lives in markdown files in a folder -- whether they use Obsidian, Logseq, Trilium, Foam, VS Code, or just a plain folder.

This prompt generalises the vault adapter to work with any folder of markdown files, adds two-way sync (keprix writes back to the vault, not just reads), and makes the vault the unified source of truth for all agent knowledge work. The user picks their UI. keprix is the AI brain that reads and writes to the same files.

## What already exists (do not rebuild)

- `research_workspace/obsidian.py` -- Obsidian vault reader (backlinks, graph export)
- `research_workspace/obsidian_routes.py` -- Obsidian API routes
- `skills/note-taking/obsidian/` -- Obsidian skill pack
- `workspace/routes/document_routes.py` -- document CRUD
- `workspace/routes/note_routes.py` -- note management
- `memory/rag/` -- RAG indexing
- `memory/episodic/` -- episodic memory
- Prompt 245 (structured workspace memory) -- auto-indexing, CLAUDE.md
- Prompt 246 (session-to-skill automation) -- skill creation loop

## What to build

### 1. Universal Vault Provider

Abstract the vault concept so keprix works with any folder of markdown files:

```python
# vault/provider.py

class VaultProvider(ABC):
    """Abstract interface for a knowledge vault -- a folder of markdown files."""

    @abstractmethod
    async def list_files(self, path: str = "/") -> list[VaultFile]: ...

    @abstractmethod
    async def read_file(self, path: str) -> str: ...

    @abstractmethod
    async def write_file(self, path: str, content: str) -> None: ...

    @abstractmethod
    async def delete_file(self, path: str) -> None: ...

    @abstractmethod
    async def search(self, query: str) -> list[VaultFile]: ...

    @abstractmethod
    async def get_backlinks(self, path: str) -> list[str]: ...

    @abstractmethod
    async def get_graph(self) -> dict: ...
    """Return the full link graph: nodes (files) and edges (links between files)."""


class LocalFolderVault(VaultProvider):
    """A plain folder of markdown files. Works with Obsidian, Logseq, Foam, etc."""

    def __init__(self, root_path: str):
        self.root = root_path

    async def write_file(self, path: str, content: str) -> None:
        full_path = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        # Preserve existing frontmatter when editing
        existing = await self.read_file(path) if os.path.exists(full_path) else ""
        merged = merge_frontmatter(existing, content)
        await aiofiles.write(full_path, merged)


class TriliumVault(VaultProvider):
    """Trilium Notes server via its REST API."""

class LogseqVault(VaultProvider):
    """Logseq graph -- same as LocalFolderVault but with Logseq-specific block refs."""
```

### 2. Vault Configuration

Users configure their vault once:

```
Settings -> Knowledge Vault

Where do your notes live?

  [x] Local folder:     ~/notes/
  [ ] Trilium server:   http://localhost:8080
  [ ] Logseq graph:     ~/Documents/logseq/
  [ ] Obsidian vault:   ~/Documents/Obsidian/

Vault type: Local Folder (auto-detected)

Sync mode:
  [x] Two-way (keprix reads and writes to your vault)
  [ ] Read-only (keprix reads your vault but never modifies it)

Indexing:
  [x] Auto-index on file change
  [x] Generate index.md files in folders
  [x] Generate CLAUDE.md navigation guide

Excluded paths:
  [.git, .trash, templates, .obsidian, logseq, _archive]

Connected: ~/notes/ (1,247 files, 42 folders)
Last indexed: 2 minutes ago
```

### 3. Two-Way Sync

keprix reads from the vault and writes back. Changes appear in the user's preferred app:

```
User creates a note in Obsidian
    -> keprix detects the file change (inotify / polling)
    -> RAG re-indexes the note
    -> Episodic memory creates an entry
    -> Folder index.md is updated
    -> Agent can now reference this note

Agent creates a wiki article during research
    -> keprix writes /wiki/portsmouth-h2-2026.md to the vault
    -> File appears in the user's Obsidian/Logseq/Trilium UI
    -> Backlinks are updated
    -> Graph view reflects the new node

User edits a note in Obsidian
    -> keprix detects the change
    -> RAG updates the embedding
    -> Memory entry is updated
    -> Index is regenerated

Agent edits a note
    -> keprix writes the change, preserving frontmatter
    -> Change appears in the user's UI immediately
    -> If the user's app has the file open, they see the update
```

Sync is async and non-blocking. File watchers trigger re-indexing within 2 seconds.

### 4. Vault-Aware Agent Context

When the agent starts, it loads the vault map:

```python
class VaultContext:
    """What the agent knows about the vault at session start."""

    root_path: str
    vault_type: str                    # "local", "trilium", "logseq"
    file_count: int
    folder_count: int
    index_files: dict[str, str]        # folder -> index.md content
    claude_md: str                     # CLAUDE.md navigation guide

    def to_system_prompt(self) -> str:
        """Generate the vault context section of the system prompt."""
        return f"""
Knowledge vault: {self.root_path} ({self.file_count} files)

Navigation: Read CLAUDE.md for the vault structure, then folder
index.md files to find specific topics. Do not scan files blindly
-- the index tells you where everything is.

Vault structure:
{self.claude_md}

Writing to the vault: Any knowledge you synthesise should be written
back to the vault as markdown files in the appropriate folder. Use
the same folder structure the user has established.
"""
```

### 5. Open-Source Alternative Integration Guides

Documentation showing users how to pair keprix with each alternative:

```
docs/vault/
  obsidian.md       - Using keprix with your Obsidian vault
  logseq.md         - Using keprix with your Logseq graph
  trilium.md        - Using keprix with your Trilium server
  foam.md           - Using keprix with Foam (VS Code)
  plain-folder.md   - Using keprix with any folder of markdown files
```

Each guide covers:
- How to configure keprix to point at the vault
- What keprix does (reads, writes, indexes, searches)
- What the app does (UI, editing, graph view, plugins)
- How they work together (two-way sync, no conflicts)
- Recommended folder structure for that app

### 6. Vault Health and Diagnostics

```bash
keprix vault doctor
```

```
Vault: ~/notes/
  Type: Local Folder (1,247 files, 42 folders)
  Status: Healthy

  Index: 1,247 files indexed, 0 pending
  Backlinks: 3,421 links resolved
  Graph: 1,247 nodes, 3,421 edges

  Last full index: 2026-07-09 14:32 UTC (2m ago)
  Last change detected: 2026-07-09 14:31 UTC (file: /raw/new-article.md)

  Warnings: None

  RAG embeddings: 1,247 documents embedded
  Memory entries: 1,247 linked to vault files
```

### 7. Migration from Old Workspace

Users with existing keprix workspace documents can migrate them to the vault:

```bash
keprix vault migrate-workspace --from ~/.keprix/workspaces/default --to ~/notes/
```

```
Migrating workspace to vault...

  documents/     -> /wiki/from-workspace/documents/   (23 files)
  notes/         -> /wiki/from-workspace/notes/       (47 files)
  research/      -> /raw/from-workspace/research/     (12 files)

  82 files migrated. Original files preserved at the source location.
  Run 'keprix vault doctor' to verify.
```

## Files to create

```
src/keprix/vault/
  __init__.py
  provider.py                 - VaultProvider base, LocalFolderVault
  providers/
    local_folder.py           - generic markdown folder
    trilium.py                - Trilium Notes API
    logseq.py                 - Logseq graph (extends local folder)
  sync.py                     - two-way sync engine, file watcher
  indexer.py                  - vault-wide indexer (extends workspace indexer from 245)
  backlinks.py                - universal backlink resolver
  graph.py                    - link graph builder
  context.py                  - VaultContext: agent system prompt generation
  config.py                   - vault configuration management
  migration.py                - workspace-to-vault migration

src/keprix/api/
  vault_routes.py             - vault configuration, health, search API
  vault_sync_routes.py        - sync status, trigger re-index

frontend/src/app/(workspace)/settings/
  vault/
    page.tsx                  - vault configuration UI
    health/
      page.tsx                - vault health and diagnostics

docs/
  vault/
    obsidian.md
    logseq.md
    trilium.md
    foam.md
    plain-folder.md
    overview.md

tests/
  vault/
    test_provider.py
    test_sync.py
    test_indexer.py
    test_backlinks.py
    test_graph.py
    test_migration.py
```

## Acceptance criteria

- User configures `~/notes/` as their vault. keprix indexes all markdown files within 30 seconds.
- Creating a file in the vault (via Obsidian, Logseq, or any editor) triggers re-indexing within 2 seconds.
- The agent creates a wiki article. The file appears in the user's vault and in their Obsidian/Logseq UI.
- `keprix vault doctor` reports vault health: file count, index status, backlinks, graph stats.
- Backlinks between notes are resolved regardless of which app created them.
- The agent reads `CLAUDE.md` on session start and navigates the vault using indexes, not file scanning.
- Migrating an existing keprix workspace to a vault preserves all documents and notes.

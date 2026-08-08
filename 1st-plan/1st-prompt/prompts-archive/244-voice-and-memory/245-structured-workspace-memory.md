# keprix - Prompt: Structured Workspace Memory with Auto-Indexing

## Purpose

Chase AI's Agentic OS video demonstrated a pattern keprix should adopt: structured folders with auto-generated indexes that tell the agent exactly what's in each directory and how to navigate it. This eliminates the "agent burns tokens searching" problem and gives the agent a map of its own memory.

keprix has documents, notes, memory, and RAG. What's missing is the navigation layer: auto-generated `index.md` files at every workspace level that act as a table of contents. The agent reads the index, knows where everything is, and goes directly to the right file.

This is cheap to build (it's markdown generation) and dramatically improves agent context loading.

## What already exists (do not rebuild)

- `workspace/routes/document_routes.py` -- document CRUD
- `workspace/routes/note_routes.py` -- notes management
- `memory/manager.py` -- memory lifecycle
- `memory/rag/` -- RAG indexing and retrieval
- `memory/episodic/` -- episodic memory store

## What to build

### 1. Workspace Template: Knowledge Processing Pipeline

A preset workspace template for processing raw information into structured knowledge and deliverables:

```
workspace/
  raw/                     - unstructured data: research, articles, transcripts, PDFs
    index.md               - auto-generated: lists all files, their topics, dates
  wiki/                    - structured summaries of raw data
    index.md               - auto-generated: topic index, links to related wiki pages
  outputs/                 - deliverables: reports, decks, drafts, exports
    index.md               - auto-generated: delivery status, linked source materials
  agents/
    CLAUDE.md              - agent navigation guide: how this workspace is organised
```

The template is available as a one-click preset when creating a new workspace or as a folder inside an existing workspace.

### 2. Auto-Generated Index Files

Every folder in the workspace gets an auto-generated `index.md`:

```markdown
# /raw -- Index

Last updated: 2026-07-09 14:32 UTC
Total files: 12 (8 processed, 4 pending)

## Files

| File | Topic | Source | Date Added | Status |
|------|-------|--------|------------|--------|
| competitor-analysis-q3.md | AI agent competitors Q3 2026 | Web research | 2026-07-05 | Processed |
| property-market-report.md | Portsmouth H2 2026 outlook | PDF extract | 2026-07-06 | Processed |
| tenant-feedback-survey.csv | Tenant satisfaction survey | Form export | 2026-07-08 | Pending |
| onboarding-call-transcript.md | Client onboarding call | Transcription | 2026-07-09 | Pending |

## Topics covered

- AI agents (3 files): competitor-analysis, pricing-research, feature-comparison
- Property market (4 files): portsmouth-outlook, southampton-yields, london-flats, rental-trends
- Client work (5 files): onboarding-call, tenant-feedback, maintenance-requests, booking-log
```

The `wiki/` index groups content by topic with links:

```markdown
# /wiki -- Knowledge Index

## AI Agents
- [Competitor landscape Q3 2026](/wiki/ai-agents/competitor-landscape-q3.md)
- [Pricing models comparison](/wiki/ai-agents/pricing-models.md)
- [Feature gap analysis vs monday.com](/wiki/ai-agents/gap-analysis-monday.md)

## Property Market
- [Portsmouth rental market H2 2026](/wiki/property/portsmouth-h2-2026.md)
- [BRR calculator methodology](/wiki/property/brr-methodology.md)

## Client Operations
- [Onboarding workflow standard](/wiki/operations/onboarding-workflow.md)
- [Maintenance request handling](/wiki/operations/maintenance-handling.md)
```

The `outputs/` index tracks deliverables:

```markdown
# /outputs -- Deliverables

| Deliverable | Status | Created | Source | Client |
|-------------|--------|---------|--------|--------|
| Portsmouth deal pack | Delivered | 2026-07-07 | /raw/property-market-report.md | Self |
| Tenant welcome guide | Draft | 2026-07-08 | /wiki/operations/onboarding.md | Flat 3 |
| Investor pitch deck | In progress | 2026-07-09 | /wiki/property/portsmouth-h2.md | Angel Investor |
```

### 3. Auto-Index Generator

The agent maintains indexes automatically:

```python
# workspace/index_generator.py

class WorkspaceIndexer:
    """Auto-generates and updates index.md files for workspace folders."""

    def __init__(self, workspace_path: str):
        self.path = workspace_path
        self.agent = IndexingAgent()  # lightweight agent for categorisation

    async def update_index(self, folder: str) -> str:
        """Regenerate the index.md for a folder."""
        files = await self.scan_folder(folder)
        categorized = await self.agent.categorize(files)
        index_content = self.render_index(folder, categorized)
        await self.write_index(folder, index_content)
        return index_content

    async def on_file_change(self, path: str, action: str):
        """Regenerate the parent folder's index on any file change."""
        folder = os.path.dirname(path)
        await self.update_index(folder)

    async def suggest_structure(self, files: list[str]) -> dict:
        """Analyse files and suggest a logical folder structure."""
        # Agent analyses file contents and proposes groupings
        # Returns: {"raw": [...], "wiki": [...], "outputs": [...]}
```

The indexer runs:
- On file create, update, or delete in any watched folder.
- On a schedule (hourly for active workspaces, daily for inactive).
- On-demand: `keprix workspace index --folder /wiki`.

### 4. Agent Navigation Guide (CLAUDE.md)

Every workspace root gets a `CLAUDE.md` (or `AGENTS.md`) that tells the agent how to navigate:

```markdown
# CLAUDE.md -- Workspace Navigation Guide

## Structure
- `/raw/` -- Unprocessed source material. Read index.md for file listing.
- `/wiki/` -- Structured knowledge articles. Read index.md for topic map.
- `/outputs/` -- Client deliverables. Read index.md for delivery status.

## Navigation pattern
When asked a question:
1. Check `/wiki/index.md` for relevant topics. Follow links to articles.
2. If not found in wiki, check `/raw/index.md` for unprocessed sources.
3. If still not found, search the web and add findings to `/raw/`.
4. After answering, consider whether the answer should become a wiki article.

## Reading strategy
- Always read the folder's index.md before scanning individual files.
- The index tells you what each file contains without loading the file.
- Only load files that are relevant to the current task.

## Writing strategy
- Add new research to `/raw/` with a descriptive filename.
- After processing raw material, summarise it into `/wiki/`.
- Deliverables go to `/outputs/` with links to source wiki articles.
```

The `CLAUDE.md` is auto-generated from the workspace template but editable by the user.

### 5. Memory-to-Index Bridge

The auto-index also connects to keprix's episodic memory:

```python
class MemoryIndexBridge:
    """Links workspace files to episodic memory entries."""

    async def link_memory(self, file_path: str):
        """When a file is created, create an episodic memory entry."""
        summary = await self.agent.summarize_file(file_path)
        await memory_manager.save(
            type="workspace_file",
            path=file_path,
            summary=summary,
            topics=self.agent.extract_topics(file_path),
        )

    async def recall_context(self, query: str) -> list[str]:
        """Search memory for relevant workspace files."""
        memories = await memory_manager.search(query, type="workspace_file")
        return [m.metadata["path"] for m in memories]
```

This means the agent can find workspace files through memory search, not just filesystem traversal.

### 6. Workspace Template Presets

Users choose from preset templates when creating a workspace:

```
New Workspace

Choose a template:
  [1] Knowledge Pipeline (/raw, /wiki, /outputs)
  [2] Property Investor (/deals, /tenants, /compliance, /reports)
  [3] Developer (/specs, /code-review, /architecture, /releases)
  [4] Client Delivery (/clients/{name}/briefs, /deliverables, /feedback)
  [5] Blank (start from scratch)

Template: Knowledge Pipeline

Workspace created at ~/.keprix/workspaces/knowledge-hub/
  /raw/     -- drop raw research here
  /wiki/    -- structured knowledge articles
  /outputs/ -- your deliverables
  CLAUDE.md -- navigation guide (read this first)

Next: Add your first file to /raw/ or ask me a question.
```

## Files to create

```
src/keprix/workspace/
  index_generator.py         - auto-index generation and maintenance
  template_presets.py        - workspace template presets
  claude_md_generator.py     - auto-generate CLAUDE.md navigation guide
  memory_index_bridge.py     - link workspace files to episodic memory

src/keprix/workspace/templates/
  knowledge_pipeline/        - /raw, /wiki, /outputs template
  property_investor/         - property domain template
  developer/                 - developer template
  client_delivery/           - client work template
  blank/                     - empty template

src/keprix/api/
  workspace_template_routes.py  - template CRUD, apply template

frontend/src/app/(workspace)/
  workspace/
    new/
      page.tsx               - workspace creation with template picker

docs/
  workspace/structured-memory.md

tests/
  workspace/
    test_index_generator.py
    test_template_presets.py
    test_memory_index_bridge.py
```

## Acceptance criteria

- Creating a new workspace with the Knowledge Pipeline template creates `/raw/`, `/wiki/`, `/outputs/` folders with auto-generated `index.md` and `CLAUDE.md`.
- Adding a file to `/raw/` automatically updates `/raw/index.md` with the file's topic and status.
- The agent reads `CLAUDE.md` on workspace load and follows the navigation pattern (index.md first, then target files).
- `keprix workspace index --folder /wiki` regenerates the index for that folder on demand.
- Workspace files are linked to episodic memory. Searching memory returns relevant file paths.
- Workspace template presets are selectable from the WebUI and CLI.

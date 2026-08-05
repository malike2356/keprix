# Keprix - Prompt 263: Brain graph export and share

**Status:** Shipped (`brain/export_json.py`, `export_obsidian.py`, `export_csv.py`, `share_links.py`, `api/brain_export_routes.py`, `api/brain_share_routes.py`, `BrainExportMenu.tsx`, `BrainExportPNG.tsx`, `BrainShareModal.tsx`, `BrainSharedGraphPage.tsx`, `/brain/share/[shareId]`, `html-to-image`, `tests/brain/test_brain_export_share.py`, `test_brain_share_links.py`). Note: prompt body header references **254**; canonical queue number is **263** per filename.

---

# Keprix - Prompt 254: Brain Graph Export and Share

## Context

The brain graph is valuable to share and to archive. A user should be able to:
- Export the current graph view as an image for a presentation or report
- Export the full brain data as a JSON or Obsidian-compatible format for backup,
  migration, or use in other tools
- Share a read-only link to their brain graph so a colleague or client can explore it
  without needing a keprix account

This is the last in the brain visualization sequence (Prompts 246-254).

## What already exists (do not rebuild)

- `BrainGraphCanvas` from Prompt 247 (use `toObject()` and `getViewport()` from React Flow)
- `GET /api/brain/graph` from Prompt 246 (full data)
- `data_architecture/exports.py` -- existing export utilities (extend, do not replace)

## What to build

### 1. PNG export (client-side)

Export the current canvas viewport as a PNG. Done client-side so no server round trip
is needed.

`frontend/src/components/brain/BrainExportPNG.tsx`:

```typescript
import { toPng } from "html-to-image";

async function exportBrainAsPNG(
  canvasElement: HTMLElement,
  filename: string = "brain-graph.png"
) {
  // Uses html-to-image to capture the React Flow canvas div as PNG.
  // Respects the current zoom and pan (exports what the user sees).
  // Options: "Full graph" (fit-view first, then export all nodes) or
  //          "Current view" (export exactly what is on screen).
  const dataUrl = await toPng(canvasElement, {
    backgroundColor: "var(--color-base)",
    pixelRatio: 2,   // 2x for retina
  });
  const link = document.createElement("a");
  link.download = filename;
  link.href = dataUrl;
  link.click();
}
```

Two export options in the UI:
- **Current view**: captures exactly the canvas viewport
- **Full graph**: calls `fitView()` on the React Flow instance first, waits for
  layout to settle (100ms), then captures. Restores the previous viewport after.

### 2. JSON export (server-side)

Exports the complete brain data as a machine-readable JSON file. Can be re-imported.

`src/keprix/brain/export_json.py`:

```python
async def export_brain_json(workspace_id: str) -> dict:
    """
    Full fidelity export of all brain nodes and edges.
    Format is keprix-native and versioned.
    """
    graph = await BrainGraphQuery().load(workspace_id, limit_nodes=10_000)
    return {
        "format": "keprix-brain-export",
        "version": "1.0",
        "exported_at": utcnow(),
        "workspace_id": workspace_id,
        "nodes": [asdict(n) for n in graph.nodes],
        "edges": [asdict(e) for e in graph.edges],
        "stats": {
            "total_nodes": graph.total_nodes,
            "total_edges": graph.total_edges,
            "nodes_by_kind": count_by_kind(graph.nodes),
        }
    }
```

HTTP endpoint:

```
GET /api/brain/export/json
Response: application/json, attachment; filename="brain-{workspace_id}-{date}.json"
```

### 3. Obsidian-compatible markdown export

Obsidian is the most widely used personal knowledge base. Users may want to move
their keprix memories into Obsidian or maintain a mirror.

`src/keprix/brain/export_obsidian.py`:

```python
async def export_brain_obsidian(workspace_id: str) -> bytes:
    """
    Exports each memory and skill as a .md file, with [[wikilinks]] representing
    edges between nodes. Returns a ZIP archive of .md files.

    File naming:
      memories/mem_abc123.md
      skills/skill_xyz.md
      sessions/sess_ghi.md (index pages only)

    Each file:
      ---
      kind: memory
      id: mem_abc123
      created: 2026-01-15T10:00:00Z
      tags: [client, invoicing]
      ---

      Client prefers PDF invoices sent on the 1st of the month.

      ## Connected to
      - [[sessions/sess_ghi789]] (derived_from)
      - [[skills/skill_send_invoice]] (used_in)
    """
```

HTTP endpoint:

```
GET /api/brain/export/obsidian
Response: application/zip, filename="brain-obsidian-{date}.zip"
```

### 4. CSV export (flat, for spreadsheets)

For users who want to work with brain data in Excel or a BI tool:

```
GET /api/brain/export/csv
Response: text/csv, filename="brain-nodes-{date}.csv"

Columns: id, kind, label, summary, created_at, edge_count, relation_types
```

Separate endpoint for edges:

```
GET /api/brain/export/csv/edges
Response: text/csv, filename="brain-edges-{date}.csv"

Columns: edge_id, source_kind, source_id, source_label, target_kind, target_id, target_label, relation, weight, created_at
```

### 5. Read-only share link

A share link lets a recipient browse the brain graph in a read-only view without
a keprix account.

`src/keprix/brain/share_links.py`:

```python
class BrainShareLink:
    share_id: str            # random, URL-safe, 20 chars
    workspace_id: str
    created_by: str          # user_id
    created_at: datetime
    expires_at: datetime | None   # None = never expires
    scope: ShareScope        # "all" | "memories_only" | "skills_only"
    password_hash: str | None     # optional password protection
    access_count: int
    last_accessed_at: datetime | None
```

HTTP endpoints:

```
POST /api/brain/share
  Body: { expires_in_days: 7 | 30 | null, scope: "all", password: "..." }
  Response: { share_id: "abc123", url: "https://keprix.app/brain/share/abc123" }

DELETE /api/brain/share/{share_id}   -- revoke

GET /api/brain/share/{share_id}/stats
  Response: { access_count, last_accessed_at, created_at, expires_at }

Public (no auth required):
GET /brain/share/{share_id}          -- shared graph view page
GET /api/brain/share/{share_id}/data -- data for the shared view (read-only, filtered by scope)
```

The shared view (`/brain/share/{share_id}`):
- Renders the full brain graph canvas (Prompt 247) in read-only mode
- Node click opens the content panel (Prompt 248) in read-only mode (no edit/delete)
- Filter bar (Prompt 249) is available
- No export, no replay, no health view (share is discovery-only)
- Header shows: "Shared brain · [workspace display name] · Read-only"
- Footer: "Explore with keprix [link]" (non-intrusive attribution)
- Password prompt if protected: shown before the graph

### 6. Export/share UI

Export menu in the graph toolbar (replaces the `[Export ▾]` placeholder from Prompt 247):

```
[Export ▾]
  ├─ PNG (current view)
  ├─ PNG (full graph)
  ├─ JSON (full data)
  ├─ Obsidian vault (ZIP)
  ├─ CSV (nodes)
  ├─ CSV (edges)
  └─ ─────────────
     Share link...
```

"Share link" opens a modal:

```
┌─────────────────────────────────────────────────────────┐
│  Share your brain graph                                 │
│                                                         │
│  Scope:  [All nodes ▾]                                  │
│  Expires: [7 days ▾]                                    │
│  Password: [______________________] (optional)          │
│                                                         │
│  [Generate link]                                        │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  https://keprix.app/brain/share/abc123xyz               │
│  [Copy] [Open in new tab]                               │
│                                                         │
│  Active links:                                          │
│  abc123xyz  ·  7d  ·  accessed 3 times  [Revoke]        │
│  def456uvw  ·  never  ·  0 accesses    [Revoke]         │
└─────────────────────────────────────────────────────────┘
```

## Files to create

```
src/keprix/brain/
  export_json.py                 - full JSON export
  export_obsidian.py             - Obsidian-compatible ZIP
  export_csv.py                  - nodes and edges CSV
  share_links.py                 - ShareLink model, create/revoke/stats

src/keprix/api/
  brain_export_routes.py         - /api/brain/export/* endpoints
  brain_share_routes.py          - /api/brain/share/* endpoints (auth + public)

frontend/src/app/brain/share/[shareId]/
  page.tsx                       - public shared graph page (no auth required)

frontend/src/components/brain/
  BrainExportMenu.tsx            - dropdown export menu
  BrainShareModal.tsx            - share link creation and management modal
  BrainExportPNG.tsx             - PNG capture utility
  BrainShareViewHeader.tsx       - read-only header for shared view

New DB table: brain_share_links
  share_id TEXT PRIMARY KEY
  workspace_id TEXT NOT NULL
  created_by TEXT NOT NULL
  created_at TEXT NOT NULL
  expires_at TEXT
  scope TEXT NOT NULL DEFAULT 'all'
  password_hash TEXT
  access_count INTEGER NOT NULL DEFAULT 0
  last_accessed_at TEXT
```

New dependency: `html-to-image` (frontend, for PNG capture).

## Acceptance criteria

- PNG export (current view) captures what is visible on screen at 2x resolution.
- PNG export (full graph) fits all nodes into frame before capturing.
- JSON export includes all nodes and edges. Re-importing it reconstructs the same graph.
- Obsidian ZIP contains one .md file per node with correct frontmatter and wikilinks.
- CSV exports produce valid files that open correctly in Excel.
- Share link is accessible without authentication. Read-only: no edit or delete actions.
- Password-protected share link shows a password prompt before revealing the graph.
- Share link expiry is enforced: expired links return a clear message, not the graph.
- Revoking a share link immediately prevents access; existing viewers lose access on next
  page load.
- Access count increments on each unique visit to the shared link.
- The shared view does not expose the workspace_id or any authenticated API endpoints.

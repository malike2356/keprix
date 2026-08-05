# Keprix - Prompt 259: Brain health and coverage dashboard

**Status:** Shipped (`brain/health.py`, `duplicates.py`, `coverage.py`, `node_flags.py`, `api/brain_health_routes.py`, `/brain/health` page, `BrainHealthScore`, `OrphanNodeList`, `DuplicateMerger`, `HubNodeList`, `CoverageGapList`, `BrainHealthOverlay`, `BrainHealthSidebarWidget`, graph overlay wiring, `tests/brain/test_brain_health.py`). Note: prompt body header references **252**; canonical queue number is **259** per filename.

---

# Keprix - Prompt 252: Brain Health and Coverage Dashboard

## Context

A growing brain accumulates noise: orphaned memories no one uses, duplicate facts
extracted from different sessions, skills that never fire, documents that were indexed
but never retrieved. Without a health view, users have no way to find and prune this
waste.

This prompt builds the Brain Health view: a dashboard overlay on the graph (and a
separate summary panel) that surfaces actionable intelligence about the brain's quality,
coverage, and gaps. It answers: is this brain healthy? What should I delete? What is
missing?

## What already exists (do not rebuild)

- `GET /api/brain/graph/stats` -- node and edge counts by kind (Prompt 246)
- `retrieval_graph_edges` -- activation frequency is implicit in edge count from node
- Brain graph canvas (Prompt 247) -- can be overlaid with health indicators

## What to build

### 1. Health metrics API

`src/keprix/brain/health.py`:

```python
class BrainHealthReport:
    workspace_id: str
    generated_at: datetime

    # Counts
    total_nodes: int
    nodes_by_kind: dict[str, int]          # {"memory": 42, "skill": 5, ...}
    total_edges: int
    edges_by_relation: dict[str, int]

    # Orphans (nodes with zero edges -- never connected to anything)
    orphan_nodes: list[GraphNode]          # sorted by age desc (oldest first)
    orphan_count: int

    # Stale nodes (connected but never retrieved in last 30 days)
    stale_nodes: list[GraphNode]
    stale_count: int

    # Hub nodes (top 10 most connected -- the brain's load-bearing memories)
    hub_nodes: list[GraphNode]

    # Duplicate candidates (memory content similarity > 0.85 but different IDs)
    duplicate_groups: list[list[GraphNode]]

    # Coverage gaps (topic areas with < 3 memories)
    coverage_gaps: list[str]              # topic labels e.g. "billing", "scheduling"

    # Freshness (average age of memory nodes in days)
    avg_memory_age_days: float

    # Overall score 0-100 (see scoring below)
    health_score: int
    health_label: str   # "Excellent" | "Good" | "Needs attention" | "Poor"
```

Health score formula:

```
score = 100
- orphan_pct * 30          (orphans as % of total nodes, max deduction 30)
- stale_pct * 20           (stale nodes as % of total, max deduction 20)
- duplicate_groups * 5     (each group of duplicates costs 5 points, max 25)
- max(0, 25 - hub_count*5) (need at least 5 hub nodes to score full marks here)
clamped to [0, 100]
```

HTTP endpoint:

```
GET /api/brain/health
  Response: BrainHealthReport (JSON)
  Cached for 5 minutes (health check is expensive, not real-time)
```

### 2. Duplicate detection

Duplicates are memories with highly similar semantic content. Two approaches, one chosen
by capability:

If embeddings are available (Prompt 230 ML service):
```python
async def find_duplicate_candidates(workspace_id: str) -> list[list[str]]:
    # Load all memory embeddings from the ML service
    # Compute cosine similarity pairwise (or use FAISS ANN for large brains)
    # Group memories with similarity > 0.85 into candidate groups
    # Return list of groups (each group = list of memory IDs)
```

If embeddings are NOT available (fallback):
```python
async def find_duplicate_candidates_fuzzy(workspace_id: str) -> list[list[str]]:
    # Use text shingling (character n-grams) + Jaccard similarity
    # Threshold: > 0.70 overlap = duplicate candidate
    # Slower but no dependency on ML service
```

### 3. Coverage gap detection

Coverage gaps are topic areas where the brain has thin knowledge (< 3 memories):

```python
async def detect_coverage_gaps(workspace_id: str) -> list[str]:
    # 1. Extract noun phrases from all memory labels using simple NLP (no LLM)
    # 2. Group memories by most-frequent noun phrase
    # 3. Report groups with < 3 memories as gap candidates
    # 4. Exclude very generic phrases ("the", "this", "that")
    # Example gaps: ["billing disputes", "cancellation policy", "GDPR requests"]
```

### 4. Health dashboard UI

Route: `/brain/health` (tab alongside `/brain/graph` and `/brain/list`)

```
┌──────────────────────────────────────────────────────────────────┐
│  Brain  [Graph] [List] [Health]                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Brain Health Score: 74 / 100  [Good]                      │  │
│  │  ████████████████░░░░░░  Last checked: 4 min ago  [Refresh]│  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Memories │  │  Skills  │  │  Tasks   │  │Documents │       │
│  │    42    │  │    5     │  │    12    │  │    3     │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                  │
│  [!] 8 orphan nodes   [!] 5 stale memories   [●] 2 duplicates  │
│                                                                  │
│  Orphan nodes (no connections)                      [View all]   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ memory  "Random thought from Jan 5"  Created 45 days ago   │  │
│  │ memory  "Scratch note - test"        Created 60 days ago   │  │
│  │                            [Delete all orphans]            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Duplicate candidates                               [View all]   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ "Client prefers PDF invoices"  ~  "PDF invoices preferred" │  │
│  │ Similarity: 91%                     [Merge] [Keep both]    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Hub nodes (most connected)                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ● "Client on Net-30 terms"  -- 12 connections             │  │
│  │  ● "Invoice template v2"     -- 9 connections              │  │
│  │  ● "sendgrid.send_email"     -- 8 connections  [View ->]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Coverage gaps (thin topic areas)                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  "GDPR requests"  -- only 1 memory  [Add memory]           │  │
│  │  "cancellation policy"  -- 0 memories  [Add memory]        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5. Graph overlay mode

From the graph canvas (Prompt 247), a "Health overlay" toggle:

When active, node colours are overridden:
- Orphan nodes: red border, warning icon
- Stale nodes: grey fill (normally coloured)
- Hub nodes: gold star badge in top-right corner
- Duplicate candidates: orange dashed border, pair arrow linking the two

This lets the user see health issues in spatial context (e.g. "all the orphans are
in the top-left cluster -- those are from the old project").

### 6. Bulk actions

From the health dashboard:

- **Delete all orphans**: confirmation dialog showing count, then batch DELETE
- **Merge duplicates**: side-by-side comparison of two candidates, pick which text
  to keep, DELETE the other, remap its edges to the survivor
- **Archive stale**: soft-archive (flag as `archived: true`) rather than hard-delete;
  archived nodes are hidden from the graph by default but recoverable

New API endpoints:

```
POST /api/brain/health/delete-orphans
  Body: { confirm: true }
  Deletes all nodes with zero edges in this workspace.

POST /api/brain/health/merge-duplicates
  Body: { keep_id: "mem_abc", delete_id: "mem_def" }
  Remaps edges from delete_id to keep_id, then deletes delete_id.

POST /api/brain/health/archive-stale
  Body: { node_ids: ["mem_xyz", ...] }
  Sets archived=true on all listed nodes. They disappear from normal graph view.
```

### 7. Health score widget in workspace sidebar

A small widget at the bottom of the workspace sidebar:

```
Brain  ████████░░  74  [View health ->]
```

Red < 40, amber 40-70, green > 70. Updates every 5 minutes.

## Files to create

```
src/keprix/brain/
  health.py                      - BrainHealthReport computation
  duplicates.py                  - duplicate detection (embedding + fuzzy fallback)
  coverage.py                    - coverage gap detection

src/keprix/api/
  brain_health_routes.py         - GET /api/brain/health
                                 - POST /api/brain/health/delete-orphans
                                 - POST /api/brain/health/merge-duplicates
                                 - POST /api/brain/health/archive-stale

frontend/src/app/(workspace)/brain/health/
  page.tsx                       - health dashboard route

frontend/src/components/brain/
  BrainHealthScore.tsx           - score card with progress bar
  OrphanNodeList.tsx             - orphan list with bulk delete
  DuplicateMerger.tsx            - side-by-side merge UI
  HubNodeList.tsx                - top connected nodes
  CoverageGapList.tsx            - thin topic areas with "Add memory" CTA
  BrainHealthOverlay.tsx         - canvas overlay mode toggle + node colouring
  BrainHealthSidebarWidget.tsx   - compact score widget for workspace sidebar
```

## Acceptance criteria

- Health score is computed correctly for a workspace with known orphan/stale/duplicate counts.
- Orphan detection correctly identifies nodes with zero entries in `retrieval_graph_edges`.
- Stale detection correctly identifies nodes with no activation events in the last 30 days.
- Duplicate detection groups two memories with > 85% similarity.
- Merge correctly remaps all edges from the deleted node to the surviving node.
- Delete-orphans removes all zero-edge nodes and confirms the count to the user.
- Health overlay on the graph canvas correctly colours orphan, stale, hub, and duplicate nodes.
- Health score widget in the sidebar updates within 5 minutes of a merge or delete action.
- Coverage gap detection returns at least 2 gaps for a brain with 10 memories on diverse topics.
- All bulk operations require explicit confirmation before executing.
- Archived nodes do not appear in normal graph view but are recoverable via a filter.

# Keprix - Prompt 246: Brain Graph API

## Context

The `retrieval_graph_edges` table (Prompt 32) already records every relationship the
agent observes between brain items: memories linked to sessions, skills referenced in
tool calls, documents cited in responses. The data is there. Nothing serves it yet.

This prompt builds the API layer that the brain visualization frontend (Prompt 247 onward)
will consume: a single endpoint that resolves all nodes and edges for a workspace brain,
enriches each node with its actual content, and supports filtering by kind, session, and
date range.

## What already exists (do not rebuild)

- `data_architecture/graph_edges.py` -- `add_graph_edge`, `list_graph_edges` (read these)
- `data_architecture/retrieval_plane.py` -- facade exposing graph edge helpers
- `data_architecture/schemas.py` -- CanonicalIds, StoragePlane, node kind vocabulary
- `api/memory_routes.py` -- memory CRUD (use to resolve memory content by ID)
- `api/skills_routes.py` -- skill CRUD (use to resolve skill content by ID)
- `api/task_routes.py` -- task CRUD (use to resolve task content by ID)

## Node kinds

```python
NODE_KINDS = {
    "memory":   "memories",       # free-form memory items
    "skill":    "skills",         # callable skill definitions
    "task":     "tasks",          # workspace tasks
    "tool":     "tools",          # keprix tools (built-in)
    "session":  "sessions",       # conversation sessions
    "document": "documents",      # uploaded or indexed documents
    "source":   "sources",        # research sources / citations
}
```

## What to build

### 1. Graph query engine

`src/keprix/brain/graph_query.py`:

```python
class BrainGraphQuery:
    """
    Resolves the full graph (nodes + edges) for a workspace brain.
    Enriches each node with a content summary and metadata.
    """

    async def load(
        self,
        workspace_id: str,
        *,
        kinds: list[str] | None = None,       # filter to specific node kinds
        session_id: str | None = None,        # only nodes touched by this session
        since: datetime | None = None,        # only nodes created/updated after
        limit_nodes: int = 500,               # cap for large brains
    ) -> BrainGraphData:
        edges = await self._load_edges(workspace_id, kinds=kinds,
                                       session_id=session_id, since=since)
        node_ids = self._collect_node_ids(edges)
        nodes = await self._resolve_nodes(workspace_id, node_ids)
        return BrainGraphData(nodes=nodes, edges=edges)

    async def _load_edges(self, workspace_id: str, **filters) -> list[GraphEdge]:
        """Query retrieval_graph_edges with optional filters."""

    async def _collect_node_ids(self, edges: list[GraphEdge]) -> set[NodeRef]:
        """Collect every unique (kind, id) pair referenced in the edge list."""

    async def _resolve_nodes(
        self, workspace_id: str, node_refs: set[NodeRef]
    ) -> list[GraphNode]:
        """
        For each (kind, id) pair, fetch the actual content from the appropriate store.
        Returns a GraphNode with: id, kind, label, summary, created_at, metadata.
        Nodes whose source record no longer exists are returned as tombstones
        (kind=kind, label="[deleted]") rather than omitted -- edges must stay valid.
        """
```

### 2. Data types

`src/keprix/brain/graph_types.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class GraphNode:
    id: str                          # source record ID
    kind: str                        # memory | skill | task | tool | session | document | source
    label: str                       # short display label (title or first 60 chars)
    summary: str                     # longer content preview (up to 200 chars)
    created_at: datetime
    updated_at: datetime | None
    metadata: dict                   # kind-specific extras (e.g. skill.trigger, task.status)
    deleted: bool = False            # True if source record no longer exists

@dataclass
class GraphEdge:
    edge_id: str
    source_kind: str
    source_id: str
    target_kind: str
    target_id: str
    relation: str                    # "derived_from" | "mentions" | "used_in" | "references" | "created_by"
    weight: float = 1.0              # higher = stronger / more frequent connection
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class BrainGraphData:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int = 0
    total_edges: int = 0
    truncated: bool = False          # True if limit_nodes was hit
```

### 3. Node content resolvers

`src/keprix/brain/node_resolvers.py`:

```python
class NodeResolver:
    """Fetches content for each node kind from its authoritative store."""

    async def resolve(self, workspace_id: str, kind: str, node_id: str) -> GraphNode | None:
        resolver = self._resolvers.get(kind)
        if not resolver:
            return None
        return await resolver(workspace_id, node_id)

    async def _resolve_memory(self, workspace_id: str, memory_id: str) -> GraphNode | None:
        """Fetch from memories table. Label = first 60 chars of content."""

    async def _resolve_skill(self, workspace_id: str, skill_id: str) -> GraphNode | None:
        """Fetch from skills table. Label = skill name. Summary = description."""

    async def _resolve_task(self, workspace_id: str, task_id: str) -> GraphNode | None:
        """Fetch from tasks table. Label = task title. Metadata includes status."""

    async def _resolve_session(self, workspace_id: str, session_id: str) -> GraphNode | None:
        """Fetch from sessions table. Label = session title or date."""

    async def _resolve_document(self, workspace_id: str, doc_id: str) -> GraphNode | None:
        """Fetch from documents table. Label = filename or title."""

    async def _resolve_tool(self, workspace_id: str, tool_id: str) -> GraphNode | None:
        """Resolve from the tool registry. Tool nodes have no workspace record."""

    async def _resolve_source(self, workspace_id: str, source_id: str) -> GraphNode | None:
        """Fetch from research sources table."""
```

### 4. HTTP endpoint

`src/keprix/api/brain_graph_routes.py`:

```
GET /api/brain/graph
  Query params:
    kinds:      comma-separated list of node kinds to include (default: all)
    session_id: filter to nodes touched by this session
    since:      ISO 8601 datetime (only nodes created after)
    limit:      max nodes to return (default 500, max 2000)

Response:
{
  "nodes": [
    {
      "id": "mem_abc123",
      "kind": "memory",
      "label": "Client prefers PDF invoices",
      "summary": "Client prefers PDF invoices sent on the 1st of the month...",
      "created_at": "2026-01-15T10:00:00Z",
      "metadata": {},
      "deleted": false
    }
  ],
  "edges": [
    {
      "edge_id": "edge_def456",
      "source_kind": "memory",
      "source_id": "mem_abc123",
      "target_kind": "session",
      "target_id": "sess_ghi789",
      "relation": "derived_from",
      "weight": 1.0,
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total_nodes": 47,
  "total_edges": 83,
  "truncated": false
}

GET /api/brain/graph/node/{kind}/{id}
  Returns full content for a single node (not just the summary).
  Used by the content panel (Prompt 248) when a node is clicked.

GET /api/brain/graph/neighbours/{kind}/{id}
  Returns all edges connected to a node plus the resolved neighbour nodes.
  Used by the focus mode (Prompt 249).

GET /api/brain/graph/stats
  Returns node counts by kind, edge counts by relation type.
  Used by the brain health dashboard (Prompt 252).
```

### 5. Edge weight computation

When `list_graph_edges` returns edges, compute weight from co-occurrence frequency:

```python
def compute_edge_weights(edges: list[GraphEdge]) -> list[GraphEdge]:
    """
    Edges between the same (source, target) pair are collapsed into one edge
    with weight = occurrence count. Higher weight = thicker edge in the UI.
    """
    counts: dict[tuple, int] = {}
    for edge in edges:
        key = (edge.source_kind, edge.source_id, edge.target_kind, edge.target_id, edge.relation)
        counts[key] = counts.get(key, 0) + 1

    seen = set()
    weighted = []
    for edge in edges:
        key = (edge.source_kind, edge.source_id, edge.target_kind, edge.target_id, edge.relation)
        if key not in seen:
            seen.add(key)
            edge.weight = counts[key]
            weighted.append(edge)
    return weighted
```

## Files to create

```
src/keprix/brain/
  __init__.py
  graph_types.py           - GraphNode, GraphEdge, BrainGraphData dataclasses
  graph_query.py           - BrainGraphQuery: load edges, resolve nodes
  node_resolvers.py        - per-kind content resolution
  edge_weights.py          - co-occurrence weight computation

src/keprix/api/
  brain_graph_routes.py    - GET /api/brain/graph and sub-endpoints

tests/brain/
  test_graph_query.py
  test_node_resolvers.py
  test_edge_weights.py
  test_brain_graph_routes.py
```

## Acceptance criteria

- `GET /api/brain/graph` returns all nodes and edges for a workspace in < 500ms for
  up to 500 nodes.
- Each node includes `label`, `summary`, `kind`, `created_at`, and `metadata`.
- Deleted source records appear as tombstone nodes (`deleted: true`) rather than
  causing 500 errors.
- `kinds` filter correctly restricts nodes and drops edges whose endpoints are excluded.
- `session_id` filter returns only nodes that appear in `retrieval_graph_edges` with
  that session as source or target.
- `GET /api/brain/graph/node/{kind}/{id}` returns full content within 100ms.
- `GET /api/brain/graph/neighbours/{kind}/{id}` returns the node and all first-degree
  connections.
- Edge weight reflects co-occurrence count. Two edges between the same pair with the
  same relation collapse into one edge with weight 2.
- Endpoint requires authentication. Returns 403 if the node belongs to a different
  workspace.

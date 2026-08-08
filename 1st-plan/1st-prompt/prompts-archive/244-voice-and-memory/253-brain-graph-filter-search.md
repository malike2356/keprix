# Keprix - Prompt 249: Brain Graph Filter, Search, and Focus Mode

## Context

A large brain can have hundreds of nodes. Without filters and search, the graph becomes
an undifferentiated blob. This prompt adds three layers of navigability:

1. **Filter bar** -- show/hide node kinds (memory, skill, task...) and date ranges
2. **Keyword search** -- find nodes whose content matches a query; highlight matches on canvas
3. **Focus mode** -- isolate one node and see only its neighbourhood; everything else dims out

These three features together let a user answer questions like "show me everything the agent
knows about invoicing" or "what did this agent do during last Tuesday's session?"

## What already exists (do not rebuild)

- `GET /api/brain/graph` accepts `kinds`, `session_id`, `since` params (Prompt 246)
- `GET /api/brain/graph/neighbours/{kind}/{id}` (Prompt 246)
- `BrainGraphCanvas` with `filters` prop (Prompt 247)
- `useBrainGraph(filters)` hook (Prompt 247)

## What to build

### 1. Filter bar component

`frontend/src/components/brain/BrainFilterBar.tsx`:

```
[Memories ●]  [Skills ●]  [Tasks ●]  [Tools ●]  [Sessions ○]  [Documents ○]  |  [Since ▾]  [Session ▾]  [Search...]  [Clear]
```

- Each kind button is a toggle. Active = filled dot + coloured border matching node colour.
- Inactive kinds are visually deselected but the button remains visible.
- Toggling a kind updates the `kinds` param passed to `useBrainGraph`, which re-queries the API.
- "Since" dropdown: Today / Last 7 days / Last 30 days / All time / Custom date
- "Session" dropdown: lists recent sessions by title; selecting one filters to nodes touched by that session
- "Clear" resets all filters to default (all kinds, all time)

### 2. Search

`frontend/src/components/brain/BrainSearchBar.tsx`:

```typescript
export function BrainSearchBar({ onResults }: { onResults: (matches: string[]) => void }) {
  // Debounced (300ms) search against /api/brain/graph/search?q=...
  // Returns list of matching node IDs.
  // Calls onResults with the IDs; canvas highlights matching nodes, dims non-matching.
  // Empty query restores normal state.
}
```

New API endpoint:

```
GET /api/brain/graph/search?q=invoicing&kinds=memory,skill&limit=50

Response:
{
  "matches": [
    { "id": "mem_abc123", "kind": "memory", "label": "...", "excerpt": "...invoicing..." },
    ...
  ]
}
```

Server-side: full-text search across each node kind's content column (LIKE %q% or FTS
depending on DB capabilities). Returns node IDs and a short excerpt with the match
highlighted in the text (`<mark>` tags stripped for the API, applied client-side).

Canvas behaviour during search:
- Matching nodes: normal colour, slight scale-up (1.1x), ring/glow effect
- Non-matching nodes: dimmed to 15% opacity
- Edges between non-matching nodes: hidden
- Edges between a matching and non-matching node: shown at 30% opacity

### 3. Focus mode

Focus mode isolates a single node and its neighbourhood. All other nodes dim out.

Activation:
- Right-click on a node -> context menu -> "Focus on this node"
- OR double-click on a node
- OR "Focus" button in the content panel (Prompt 248)

```typescript
export function useFocusMode(canvas: ReactFlowInstance) {
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);

  function focusNode(nodeId: string) {
    setFocusedNodeId(nodeId);
    // Fetches /api/brain/graph/neighbours/{kind}/{id}
    // Gets the IDs of all first-degree neighbours
    // Sets all OTHER nodes to opacity 0.1
    // Sets all edges not touching the focused node to opacity 0.05
    // Fits the view to the focused node + its neighbours
  }

  function clearFocus() {
    setFocusedNodeId(null);
    // Restores all nodes and edges to normal opacity
    // Fits view back to full graph
  }

  return { focusedNodeId, focusNode, clearFocus };
}
```

When focus mode is active, a dismissal banner appears at the top of the canvas:

```
[●] Focused on: "Client prefers PDF invoices"  [Show full graph]
```

### 4. Depth control in focus mode

When focused, a depth slider lets the user expand the neighbourhood:

```
Depth: [1] [2] [3]
```

- Depth 1: direct neighbours only
- Depth 2: neighbours-of-neighbours (2 hops)
- Depth 3: 3 hops

New API:

```
GET /api/brain/graph/neighbours/{kind}/{id}?depth=2
```

Server-side: BFS from the focal node up to `depth` hops. Returns all nodes and edges
in the subgraph. Capped at 100 nodes to prevent full-graph return.

### 5. Filter state persistence

Filter preferences are persisted in `localStorage` per workspace so they survive
page refreshes:

```typescript
const FILTER_KEY = `brain-graph-filters-${workspaceId}`;
```

Persisted: kind toggles, default since range. NOT persisted: search query, focus mode
(these are ephemeral per-session navigation choices).

### 6. URL state

Filter state is reflected in the URL so links can be shared:

```
/brain/graph?kinds=memory,skill&since=7d&q=invoicing
```

`useSearchParams` / `router.replace` to keep URL in sync without adding browser history
entries on every keystroke. Search query uses `replace`, not `push`.

## Files to create

```
frontend/src/components/brain/
  BrainFilterBar.tsx             - kind toggles + date + session dropdowns
  BrainSearchBar.tsx             - debounced search input
  BrainFocusBanner.tsx           - "focused on X / show full graph" banner

frontend/src/hooks/
  useBrainFilters.ts             - filter state, URL sync, localStorage persistence
  useFocusMode.ts                - focus/unfocus, depth BFS, opacity management

src/keprix/api/
  brain_graph_search.py          - GET /api/brain/graph/search
```

Extended in Prompt 246's `brain_graph_routes.py`:
- `GET /api/brain/graph/neighbours/{kind}/{id}?depth=N` -- BFS to depth N

## Acceptance criteria

- Kind filter toggles correctly show/hide node kinds and re-query the API.
- Date range filter "Last 7 days" shows only nodes created in the last 7 days.
- Session filter shows only nodes connected to the selected session.
- Keyword search highlights matching nodes and dims non-matching within 400ms of the last keystroke.
- Matching nodes show an excerpt with the matched text.
- Focus mode isolates a node and its depth-1 neighbours. Non-neighbours dim to 15% opacity.
- Depth slider in focus mode expands to depth 2 and 3 correctly.
- Focus mode dismissal banner restores the full graph.
- Filter preferences survive page refresh (localStorage).
- Active filters are reflected in the URL and can be restored by sharing the URL.
- "Clear" resets all filters including the URL params.

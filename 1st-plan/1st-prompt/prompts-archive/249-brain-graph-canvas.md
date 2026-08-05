# Keprix - Prompt 247: Brain Graph Canvas (React Flow)

## Context

Prompt 246 delivers the API. This prompt builds the interactive canvas that renders it:
a zoomable, pannable force-directed graph where every node is a real brain item and every
edge is a relationship the agent has observed. Clicking a node opens its full content
(Prompt 248). Filtering is in Prompt 249. Live activation is in Prompt 250.

This is the view that makes keprix's memory visible for the first time. The closest
comparable product is Obsidian's graph view, but keprix's version shows agent-generated
relationships rather than user-written wiki links, and it is live rather than static.

React Flow is already referenced in Prompt 233 (Visual Playbook Studio). Use the same
dependency. The two canvases are distinct routes; they share the library, not components.

## What already exists (do not rebuild)

- `frontend/package.json` -- `@xyflow/react` (React Flow v12) installed for Prompt 233
- `GET /api/brain/graph` -- data API from Prompt 246
- `frontend/src/app/(workspace)/` -- route host pattern from Prompts 225-227

## Route

```
/brain/graph
```

Added to workspace nav under "Brain" section (same section as /library, /tasks).

## Node visual design

Each node kind has a distinct colour and shape so the user can read the graph at a glance
without reading labels:

```
memory    -- soft blue circle         #3b82f6
skill     -- amber diamond            #f59e0b
task      -- emerald square           #10b981
tool      -- slate hexagon            #64748b
session   -- purple rounded rect      #8b5cf6
document  -- orange folded rect       #f97316
source    -- rose circle              #f43f5e
```

Label: first 40 characters of the node's `label` field, truncated with ellipsis.
Size: scaled by degree (number of edges). Minimum 36px diameter, maximum 72px.

## What to build

### 1. Data fetching hook

`frontend/src/hooks/useBrainGraph.ts`:

```typescript
export function useBrainGraph(filters: BrainGraphFilters) {
  // Fetches /api/brain/graph with current filter params.
  // Returns { nodes, edges, loading, error, refetch }.
  // Transforms API response into React Flow node/edge format.
  // Polls every 30 seconds when the tab is focused (brain grows during sessions).
}
```

### 2. Node transformation

`frontend/src/components/brain/graph-transform.ts`:

```typescript
export function apiToFlowNodes(apiNodes: GraphNode[]): Node[] {
  // Convert BrainGraphData.nodes to React Flow Node[] format.
  // Assigns position via force simulation (see Prompt 251 for layout engine).
  // Initial positions: random within a 2000x2000 virtual canvas.
  // React Flow's built-in layout hook handles subsequent positioning.
}

export function apiToFlowEdges(apiEdges: GraphEdge[]): Edge[] {
  // Convert BrainGraphData.edges to React Flow Edge[] format.
  // Edge strokeWidth = log(weight + 1) * 2 (thicker for higher weight).
  // Edge label = relation string, shown on hover only.
  // Animated dashes for "derived_from" edges; solid for "references".
}
```

### 3. Custom node components

`frontend/src/components/brain/nodes/`:

```
MemoryNode.tsx      -- blue circle, memory icon, label
SkillNode.tsx       -- amber diamond, bolt icon, label
TaskNode.tsx        -- emerald square, check icon, label + status dot
ToolNode.tsx        -- slate hexagon, wrench icon, label
SessionNode.tsx     -- purple rounded rect, chat icon, label + date
DocumentNode.tsx    -- orange folded rect, file icon, label
SourceNode.tsx      -- rose circle, link icon, label
DeletedNode.tsx     -- greyed-out version for tombstoned nodes
```

Each node component:
- Renders the correct shape and colour
- Shows the label, truncated
- Shows a tooltip on hover with the full `summary` field
- On click: emits `onNodeClick(node)` to open the content panel (Prompt 248)
- On hover: highlights all directly connected edges and neighbour nodes;
  dims everything else

### 4. Canvas component

`frontend/src/components/brain/BrainGraphCanvas.tsx`:

```typescript
export function BrainGraphCanvas({ filters, onNodeSelect }: BrainGraphCanvasProps) {
  const { nodes, edges, loading } = useBrainGraph(filters);
  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);

  useEffect(() => {
    setFlowNodes(apiToFlowNodes(nodes));
    setFlowEdges(apiToFlowEdges(edges));
  }, [nodes, edges]);

  return (
    <ReactFlow
      nodes={flowNodes}
      edges={flowEdges}
      nodeTypes={NODE_TYPES}
      onNodeClick={(_, node) => onNodeSelect(node.data)}
      fitView
      minZoom={0.1}
      maxZoom={3}
    >
      <Background variant="dots" gap={20} size={1} color="var(--color-border)" />
      <Controls />
      <MiniMap nodeColor={nodeKindColor} zoomable pannable />
      {loading && <GraphLoadingOverlay />}
    </ReactFlow>
  );
}
```

### 5. Page layout

`frontend/src/app/(workspace)/brain/graph/page.tsx`:

```
┌───────────────────────────────────────────────────────────────┐
│  Brain  [Graph] [List] [Health]        [Filter ▾] [Export ▾]  │  <- tab bar
├─────────────────────────────────────────┬─────────────────────┤
│                                         │                     │
│                                         │  Content panel      │
│   React Flow canvas (full height)       │  (Prompt 248)       │
│                                         │  slides in when     │
│                                         │  a node is clicked  │
│                                         │                     │
│                                         │  Hidden by default. │
│                                         │  300px wide.        │
│                                         │                     │
└─────────────────────────────────────────┴─────────────────────┘
```

The content panel is rendered as a CSS slide-in from the right. The canvas
shrinks by 300px when the panel is open; it does not overlay.

### 6. Empty state

When the brain has no edges yet (new workspace, agent has not yet extracted anything):

```
[empty graph icon]
Your brain is empty.
Start a conversation and keprix will map connections automatically.
[Start a chat ->]
```

### 7. Loading state

While the API call is in flight, show a skeleton canvas:
- 8-12 placeholder circles of varying sizes, greyed out
- Animated pulse
- Placeholder edges as dashed lines between them

## Files to create

```
frontend/src/app/(workspace)/brain/graph/
  page.tsx                  - route page, layout shell

frontend/src/components/brain/
  BrainGraphCanvas.tsx      - React Flow canvas wrapper
  BrainGraphPage.tsx        - page composition (canvas + panel + filter bar)
  graph-transform.ts        - API response -> React Flow format
  GraphLoadingOverlay.tsx   - loading spinner overlay on canvas
  GraphEmptyState.tsx       - empty brain call-to-action

frontend/src/components/brain/nodes/
  MemoryNode.tsx
  SkillNode.tsx
  TaskNode.tsx
  ToolNode.tsx
  SessionNode.tsx
  DocumentNode.tsx
  SourceNode.tsx
  DeletedNode.tsx
  node-kinds.ts             - colour map, shape constants, NODE_TYPES registry

frontend/src/hooks/
  useBrainGraph.ts          - data fetching and polling

frontend/src/types/
  brain-graph.ts            - TypeScript types matching Prompt 246 API response
```

## Acceptance criteria

- `/brain/graph` renders a React Flow canvas with all workspace brain nodes and edges.
- Each node kind renders with the correct colour and shape.
- Node size scales with degree. The most connected node is largest.
- Clicking a node opens the content panel (Prompt 248 shell; panel content can be
  stubbed until 248 is implemented).
- Hovering a node highlights its edges and neighbours; dims unconnected nodes to 20% opacity.
- Edge strokeWidth reflects weight. An edge with weight 5 is visibly thicker than one
  with weight 1.
- Canvas is zoomable (mouse wheel) and pannable (drag). MiniMap shows current viewport.
- Deleted nodes render in grey with "[deleted]" label; they do not break edge rendering.
- Empty state renders correctly when zero edges exist.
- Loading skeleton renders during the initial API fetch.
- Page loads under 2 seconds for a brain with 200 nodes and 400 edges.

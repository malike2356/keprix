# Keprix - Prompt 257: Brain graph layout engine and clustering

**Status:** Shipped (`frontend/src/lib/brain/layout-*.ts`, `force-layout.worker.ts`, `BrainLayoutSwitcher.tsx`, `BrainMinimap.tsx`, `ClusterBubble.tsx`, `clustering.ts`, `BrainGraphCanvas.tsx` integration, `d3-force` dependency, `layout-engine.test.ts`, `layout-registry.test.ts`). Note: prompt body header references **251**; canonical queue number is **257** per filename.

---

# Keprix - Prompt 251: Brain Graph Layout Engine and Clustering

## Context

Prompt 247 places nodes at random positions and relies on React Flow's default
force simulation for layout. For small brains (< 50 nodes) this is fine.
For large brains (200+ nodes) it produces hairball clusters that are unreadable.

This prompt gives the user four named layout modes, an automatic clustering algorithm
that groups strongly connected nodes, and a minimap that stays useful at all scales.

## What already exists (do not rebuild)

- `@xyflow/react` with built-in force layout utilities
- `BrainGraphCanvas.tsx` from Prompt 247 (modify, do not replace)
- `apiToFlowNodes`, `apiToFlowEdges` from Prompt 247 (replace with layout-aware versions)

## Four layout modes

### Force-directed (default)

Standard D3-style force simulation. Nodes repel each other, edges attract.
Node size and edge weight influence force magnitudes.

Best for: small to medium brains, discovery exploration.

Implementation: `@xyflow/react`'s `useNodesInitialized` + `d3-force` applied as a
post-layout pass:

```typescript
function applyForceLayout(nodes: Node[], edges: Edge[]): Node[] {
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(edges).id(d => d.id).distance(120).strength(0.5))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("collision", d3.forceCollide().radius(d => d.data.radius + 20))
    .force("center", d3.forceCenter(0, 0));
  // Run simulation synchronously for 300 ticks, return final positions
}
```

### Temporal (left-to-right by creation date)

Nodes sorted by `created_at`. Older nodes on the left, newer on the right.
Y-axis: spread by kind (memory row, skill row, session row...).

Best for: tracing how the brain evolved over time.

```
[sessions]   sess_001  sess_002  sess_003  sess_004
[memories]   mem_001  mem_002  mem_003
[skills]              skill_001  skill_002
             Jan 10   Jan 15   Jan 20   Jan 25
```

### Radial (by kind, from centre)

Centre of canvas: session nodes (they are the root cause of all other nodes).
Ring 1: memories and documents (extracted from sessions).
Ring 2: skills (derived from repeated patterns in memories).
Ring 3: tools (called by skills).
Ring 4: sources (referenced by documents).

Best for: understanding the dependency graph structure.

### Hierarchical (by connectivity, top-to-bottom)

Nodes ranked by degree (most edges = top of hierarchy).
High-degree hub nodes at the top. Leaf nodes at the bottom.
Implemented with a simple topological sort + layer assignment.

Best for: finding the most important/connected nodes quickly.

## Clustering

Clusters are groups of nodes that are more connected to each other than to the
rest of the graph. Visualised as a transparent background bubble behind the cluster.

`frontend/src/components/brain/clustering.ts`:

```typescript
export function detectClusters(nodes: Node[], edges: Edge[]): ClusterGroup[] {
  // Simple community detection: connected components first,
  // then Louvain-lite (greedy modularity maximisation).
  // For brains < 100 nodes: connected components is sufficient.
  // For larger brains: Louvain gives meaningful topic clusters.
  // Each cluster gets a label derived from the most common word in node labels.
  // Returns: [{ id, nodeIds, label, centroid }]
}
```

Cluster rendering:
- A `<ClusterBubble>` rendered as a React Flow background node (non-interactive,
  z-index behind content nodes).
- Soft fill: kind colour of the dominant node kind at 8% opacity.
- Dashed border.
- Cluster label in the top-left corner of the bubble.

Clusters are recomputed when the graph data changes but NOT on every layout animation
frame (they are expensive -- compute once per data load).

## Layout switcher UI

Toolbar button group in the canvas top-right:

```
[Force] [Time] [Radial] [Hierarchy]   [Clusters ●]
```

- Active layout highlighted.
- Switching layout triggers a smooth animated re-layout (200ms transition on node positions).
- "Clusters" toggle shows/hides cluster bubbles. Independent of layout mode.
- Layout preference saved to localStorage per workspace.

Layout transition animation:

```typescript
function animateLayout(
  currentNodes: Node[],
  targetPositions: Record<string, XYPosition>,
  duration = 300,
) {
  // Interpolate each node's position from current to target over `duration` ms.
  // Uses requestAnimationFrame.
  // Nodes that are in the same position (unmoved) skip animation.
}
```

## Minimap improvements

The default React Flow minimap does not distinguish node kinds.

Custom minimap:

```typescript
function BrainMinimap({ nodes, viewport }: ...) {
  // SVG minimap.
  // Each node rendered as a tiny circle with the kind's colour.
  // Viewport rectangle shown as a white/grey outline.
  // Click on minimap pans the canvas to that position.
  // Shows cluster bubbles as faint coloured regions.
}
```

## Performance: incremental layout

For brains > 200 nodes, full force simulation on every data change is slow.

Incremental layout: only re-simulate nodes and edges that have changed since the last
layout. Existing nodes keep their positions; new nodes are placed near the node they
are most connected to.

```typescript
function incrementalLayout(
  existingPositions: Record<string, XYPosition>,
  newNodes: Node[],
  allEdges: Edge[],
): Record<string, XYPosition> {
  // For each new node: find its highest-weight edge to an existing node.
  // Place new node at: existing_node_position + random_offset(radius=100).
  // Run force simulation only for the new nodes, fixing existing node positions.
}
```

## Files to create or modify

```
frontend/src/components/brain/
  BrainLayoutSwitcher.tsx         - layout mode toggle buttons
  BrainMinimap.tsx                - custom kind-aware minimap
  ClusterBubble.tsx               - transparent cluster background node
  clustering.ts                   - cluster detection algorithm

frontend/src/lib/brain/
  layout-force.ts                 - force-directed layout (d3-force)
  layout-temporal.ts              - temporal (left-to-right by date)
  layout-radial.ts                - radial by kind
  layout-hierarchical.ts          - hierarchical by degree
  layout-incremental.ts           - incremental layout for large brains
  layout-animate.ts               - position interpolation animation
  layout-registry.ts              - { id, label, apply } registry of layouts
```

Modifications to existing files:
- `BrainGraphCanvas.tsx` -- replace random initial positions with layout engine call;
  add layout switcher toolbar; integrate custom minimap
- `apiToFlowNodes` -- accept computed positions from layout engine

New dependency: `d3-force` (add to frontend/package.json).

## Acceptance criteria

- All four layout modes render correctly and produce non-overlapping nodes for a brain
  with 100 nodes.
- Switching layouts animates smoothly in < 300ms.
- Cluster detection finds at least 2 meaningful clusters in a brain with 50+ nodes.
- Cluster bubbles render behind content nodes and do not interfere with interaction.
- Custom minimap colours nodes by kind and shows cluster regions.
- Incremental layout adds new nodes near their most-connected existing neighbour.
- Layout preference persists across page reloads (localStorage).
- Force simulation runs synchronously (not blocking the main thread): runs in a Web
  Worker for graphs with > 100 nodes.
- On a brain with 300 nodes, initial layout completes in < 2 seconds.

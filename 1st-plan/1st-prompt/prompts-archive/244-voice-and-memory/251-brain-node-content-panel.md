# Keprix - Prompt 248: Brain Node Content Panel

## Context

Prompt 247 renders the graph canvas. When a user clicks a node, they need to see the
actual content behind it -- the full memory text, the skill definition, the task body --
without leaving the graph view. This prompt builds the slide-in content panel that opens
on the right side of the canvas when any node is selected.

The panel is the primary interaction surface of the brain graph. It is what turns the
graph from a visualization into a functional tool: you can read, edit, delete, and
navigate the brain from within the graph without going to separate pages.

## What already exists (do not rebuild)

- `GET /api/brain/graph/node/{kind}/{id}` -- full content endpoint from Prompt 246
- `BrainGraphCanvas` -- emits `onNodeSelect(node)` from Prompt 247
- Existing edit UIs for memory, skill, task (reuse their forms, do not rebuild)

## What to build

### 1. Panel shell

`frontend/src/components/brain/NodeContentPanel.tsx`:

```typescript
interface NodeContentPanelProps {
  node: GraphNode | null;
  onClose: () => void;
  onNavigateTo: (kind: string, id: string) => void; // re-center graph on another node
}

export function NodeContentPanel({ node, onClose, onNavigateTo }: NodeContentPanelProps) {
  // Slides in from the right when node is non-null.
  // Width: 320px on desktop, full-screen drawer on mobile.
  // Fetches full content from /api/brain/graph/node/{kind}/{id} when node changes.
  // Renders the correct content component based on node.kind.
}
```

Panel sections (always present regardless of kind):

```
┌─────────────────────────────────────────┐
│ [kind badge]  Node label         [X]    │  <- header
├─────────────────────────────────────────┤
│                                         │
│  [Kind-specific content]                │
│                                         │
├─────────────────────────────────────────┤
│  Connected to (N)                       │  <- connections section
│  ○ [memory] "another memory"   [->]     │
│  ○ [session] "Chat on Jan 15"  [->]     │
│  ○ [skill] "Send email"        [->]     │
├─────────────────────────────────────────┤
│  [Edit]  [Delete]  [Open full page ->]  │  <- actions footer
└─────────────────────────────────────────┘
```

### 2. Kind-specific content components

`frontend/src/components/brain/panel-content/`:

**MemoryPanelContent.tsx**
```
Created: Jan 15, 2026
─────────────────────
[full memory text, no truncation]
─────────────────────
Tags: [client] [invoicing]
Confidence: 0.92
Extracted from: [session link]
```

**SkillPanelContent.tsx**
```
Trigger: "send payment reminder"
─────────────────────
[skill description]
─────────────────────
Actions: sendgrid.send_email, crm.log_activity
Last used: 2 days ago
Used N times
```

**TaskPanelContent.tsx**
```
Status: [In Progress]    Due: Jan 20
─────────────────────
[task body]
─────────────────────
Created in session: [session link]
```

**SessionPanelContent.tsx**
```
Jan 15, 2026  14:23 -- 14:51  (28 min)
─────────────────────
[first 3 messages, abbreviated]
  You: "check the calendar for next week..."
  Aiva: "I found 3 appointments..."
─────────────────────
[View full session ->]
Memories extracted: 3
Skills used: 2
```

**DocumentPanelContent.tsx**
```
document.pdf  ·  42 pages  ·  Indexed Jan 10
─────────────────────
[excerpt from the document most relevant to its graph connections]
─────────────────────
[Open document ->]
Referenced in: 5 memories
```

**ToolPanelContent.tsx**
```
sendgrid.send_email
─────────────────────
[tool description]
Parameters: to, subject, body, template_id
─────────────────────
Used 23 times across 8 sessions
Last called: yesterday
```

**SourcePanelContent.tsx**
```
[source title]
[url or citation]
─────────────────────
[excerpt]
─────────────────────
[Open source ->]
Cited in: 2 memories
```

### 3. Connections section

Below the content, show all first-degree neighbours fetched from
`GET /api/brain/graph/neighbours/{kind}/{id}`:

```typescript
function ConnectionsList({ kind, id, onNavigateTo }: ...) {
  // Groups neighbours by kind.
  // Each neighbour shows: kind badge, label (truncated 40 chars), relation label, arrow button.
  // Clicking the arrow button calls onNavigateTo(kind, id) which re-centers the graph
  // on that node AND updates the panel to show that node's content.
  // Shows max 10 connections. "Show all N" expands.
}
```

### 4. Inline edit

The "Edit" button in the footer opens an inline edit form within the panel.
It does not navigate away from the graph.

```typescript
function MemoryEditForm({ memory, onSave, onCancel }: ...) {
  // Reuses the same PATCH /api/memories/{id} endpoint.
  // On save: re-fetches the node, updates the panel content.
  // On save: graph node label also updates in the canvas (via shared state or refetch).
}
```

Each kind has a minimal edit form (text area for memories, name/description for skills,
title/status for tasks). Tools are read-only (built-in, not editable).

### 5. Delete with edge cleanup

"Delete" on a memory/skill/task:
- Shows confirmation: "Delete this [kind]? N connections will also be removed."
- On confirm: calls the existing DELETE endpoint for that kind
- Also calls a new `DELETE /api/brain/graph/edges?source_kind=&source_id=` to clean orphan edges
- Removes the node from the canvas (soft removal -- node turns into a DeletedNode briefly, then fades out)

### 6. Navigation behaviour

- When the user clicks a connection's arrow `[->]`, the graph canvas re-centers on that node
  and the panel slides to show the new node's content.
- The panel maintains a back/forward navigation stack (like a browser):
  `[<] Memory > Session > Skill [>]`
- Back/forward arrows appear in the panel header once history depth > 1.

## Files to create

```
frontend/src/components/brain/
  NodeContentPanel.tsx           - panel shell, slide-in animation, fetch logic
  ConnectionsList.tsx            - neighbour list with navigate-to arrows

frontend/src/components/brain/panel-content/
  MemoryPanelContent.tsx
  SkillPanelContent.tsx
  TaskPanelContent.tsx
  SessionPanelContent.tsx
  DocumentPanelContent.tsx
  ToolPanelContent.tsx
  SourcePanelContent.tsx
  DeletedPanelContent.tsx        - tombstone content (deleted item notice)
  panel-registry.ts              - kind -> component mapping

frontend/src/components/brain/panel-edit/
  MemoryEditForm.tsx
  SkillEditForm.tsx
  TaskEditForm.tsx
  panel-edit-registry.ts         - kind -> edit form mapping
```

## Acceptance criteria

- Clicking a node opens the content panel without navigating away from the graph.
- The panel fetches and displays full content (not just the summary) for every node kind.
- Connections section lists all first-degree neighbours grouped by kind.
- Clicking a connection's arrow re-centers the graph on that node and updates the panel.
- Panel back/forward navigation works correctly across at least 5 hops.
- Inline edit saves correctly and the graph node label updates without a full page reload.
- Delete removes the node from the canvas with a fade animation and cleans orphan edges.
- Panel is responsive: full-screen drawer on viewports < 768px.
- Panel opens in < 200ms (optimistic render with skeleton, then content fills in).
- Tools panel is read-only. Edit/delete buttons are hidden for tool nodes.

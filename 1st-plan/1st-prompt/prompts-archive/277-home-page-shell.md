# Keprix - Prompt 261: Home Page Shell

## UI entry point

Primary location: `/` (root, redirects to `/home` internally if needed)
Secondary locations: Keprix logo click from any page
Empty state: Welcome screen for zero-session workspaces (spec below)
Discovery trigger: The home page IS the discovery surface -- it hosts the discovery card system
Nav placement: First item in left nav, always visible

## Context

The home page is the first thing a user sees when they open keprix and the place they
return to between sessions. It must answer three questions immediately without the user
scanning for them:

1. What is happening right now? (active tasks, live sessions)
2. What was I doing? (recent sessions)
3. What should I do next? (discovery card, start session button)

It is not a metrics dashboard. It does not have charts showing token usage over time or
node count graphs. Those belong in `/admin/quotas` and `/brain/health`. The home page
is a launchpad and an orientation point. It should load fast, feel calm, and make the
next action obvious.

## What already exists (do not rebuild)

- `src/app/layout.tsx` -- root layout with left nav shell
- `src/components/launcher/LauncherExpanded.tsx` -- launcher overlay (separate from home)
- `GET /api/sessions` -- session list endpoint (use `?limit=5&order=desc`)
- `GET /api/tasks` -- task list endpoint (use `?status=running&limit=3`)
- `GET /api/workspace/settings` -- workspace settings (name, user display name)
- `GET /api/brain/stats` -- brain stats endpoint (from Prompt 246: node counts by kind)
- `GET /api/admin/quotas` -- quota usage (from Prompt 258)
- Left nav component with active state handling
- User session/auth context (`useWorkspace`, `useUser` hooks)

## Data the page needs

All data fetched server-side (Next.js server component) except the discovery card
(client-side because it reads localStorage for dismissed state).

```typescript
// Parallel fetches, all with 10s timeout, all non-blocking on error
const [sessions, tasks, brainStats, quotaUsage, workspace] = await Promise.allSettled([
  fetchSessions({ limit: 5, order: 'desc' }),
  fetchTasks({ status: ['running', 'queued'], limit: 3 }),
  fetchBrainStats(),
  fetchQuotaUsage(),       // null if quotas not configured for this product
  fetchWorkspaceSettings(),
])
```

Each widget renders its own loading skeleton and error state independently. A failed
`fetchTasks` does not blank the whole page -- the tasks widget shows "Could not load
tasks" and the rest of the page renders normally.

## Page layout

Three-row layout. No sidebar within the page. Full content width minus the left nav.

```
┌────────────────────────────────────────────────────────────────┐
│  Row 0: Greeting bar                                           │
│  "Good morning, [name]."           [+ Start session]          │
├──────────────────────────────┬─────────────────────────────────┤
│  Row 1a: Recent sessions     │  Row 1b: Brain + Tasks stack   │
│  (flex-grow, ~60% width)     │  (~40% width, fixed)           │
│                              │  ┌─────────────────────────┐   │
│  Session card x 3-5          │  │  Brain widget           │   │
│                              │  └─────────────────────────┘   │
│  [See all sessions]          │  ┌─────────────────────────┐   │
│                              │  │  Active tasks widget    │   │
│                              │  └─────────────────────────┘   │
├──────────────────────────────┴─────────────────────────────────┤
│  Row 2: Discovery card (conditional, see below)                │
└────────────────────────────────────────────────────────────────┘
```

Responsive breakpoints:
- >= 1024px: two-column layout as above
- < 1024px: single column, stacked: greeting, sessions, brain widget, tasks widget,
  discovery card
- < 640px (mobile): same single column, reduced padding, session cards simplified

## Component specifications

---

### GreetingBar

```typescript
// src/components/home/GreetingBar.tsx
// Server component -- reads server time, no client JS needed

function getGreeting(hour: number): string {
  if (hour >= 5 && hour < 12) return 'Good morning'
  if (hour >= 12 && hour < 18) return 'Good afternoon'
  if (hour >= 18 && hour < 22) return 'Good evening'
  return 'Working late'    // 22:00 - 04:59
}
```

Layout:
```
Good morning, [display name].        [+ Start session]
```

- Display name from `workspace.userDisplayName`, fallback to email prefix
- "Start session" is a primary button, always visible, links to `/sessions/new`
- The greeting line is `text-2xl font-semibold`, subdued color
- No avatar, no status indicator -- those belong in the nav, not the heading

---

### RecentSessionsWidget

```typescript
// src/components/home/RecentSessionsWidget.tsx
// Shows the last N sessions. N = 5 on desktop, 3 on mobile.
```

**Session card (within this widget):**

```
┌──────────────────────────────────────────────────────────────┐
│  Drafted invoice for Kofi Mensah                             │
│  2 hours ago  ·  4 messages  ·  2 memories  ·  1 skill      │
│                                          [Resume ->]         │
└──────────────────────────────────────────────────────────────┘
```

- Title: session title (auto-generated from first message, max 60 chars, truncated)
- Metadata row: relative time, message count, memory count, skill count
  - Show only non-zero metadata items (if skills = 0, do not show "0 skills")
- "Resume" links to `/sessions/[id]`
- Entire card is clickable (same as Resume)
- Hover state: subtle border highlight, no transform

**Loading state:** Three skeleton cards, same height as real cards.

**Error state:** "Could not load recent sessions. [Refresh]"

**Footer:** "[See all sessions ->" link to `/sessions`

**Empty state (zero sessions):** Do not render this widget. Instead the full page
shows the welcome empty state (see below).

**When to show "View in brain":** Only on cards where `memoryCount > 0`. Appears as
a secondary link alongside "Resume":

```
[Resume ->]   [View in brain]
```

---

### BrainWidget

```typescript
// src/components/home/BrainWidget.tsx
// Summary of the brain: node counts, health score, last update time.
```

```
┌──────────────────────────────────┐
│  Brain                           │
│                                  │
│  342  memories                   │
│   12  skills                     │
│    8  documents                  │
│    3  sources                    │
│                                  │
│  Health: 94 / 100                │
│  Last updated: 2 minutes ago     │
│                                  │
│  [Open brain graph ->]           │
└──────────────────────────────────┘
```

- Node counts from `brainStats.nodesByKind`
- Health score from `brainStats.healthScore` (from Prompt 252)
  - Score displayed as: `94 / 100` with a thin progress bar underneath
  - Color: green >= 80, amber 60-79, red < 60
- "Last updated" = most recent `created_at` across all brain nodes
- "Open brain graph ->" links to `/brain/graph`

**Empty state (zero brain nodes):**

```
┌──────────────────────────────────┐
│  Brain                           │
│                                  │
│  Empty. Start a session and      │
│  your agent will begin building  │
│  its memory here.                │
│                                  │
│  [Learn more ->]                 │
└──────────────────────────────────┘
```

**Loading state:** Skeleton rows matching the node count list.

**Error state:** "Brain stats unavailable." (small, non-alarming)

---

### ActiveTasksWidget

```typescript
// src/components/home/ActiveTasksWidget.tsx
// Shows running and queued tasks. Polls every 15 seconds if tasks are active.
// Client component (needs polling).
```

```
┌──────────────────────────────────┐
│  Active tasks              (3)   │
│                                  │
│  Research: borehole market       │
│  Running  ·  Step 3 of 7        │
│  [Watch live ->]                 │
│                                  │
│  Draft Q2 report                 │
│  Queued                          │
│                                  │
│  [See all tasks ->]              │
└──────────────────────────────────┘
```

- Shows up to 3 active/queued tasks
- Each task shows: title, status (Running / Queued / Paused), step progress if available
- "Watch live ->" links to `/tasks/[id]` with the live view open
- Polls `GET /api/tasks?status=running,queued&limit=3` every 15 seconds when the
  widget is mounted and at least one task is active. Stops polling when all tasks
  complete or the page is hidden (`document.visibilityState`).

**Empty state (no active tasks):**

```
┌──────────────────────────────────┐
│  Active tasks                    │
│                                  │
│  No tasks running.               │
│  Ask your agent to work on       │
│  something while you do other    │
│  things.                         │
└──────────────────────────────────┘
```

Do not show "[See all tasks ->]" in the empty state -- it would lead to another empty page.

**Loading state:** Two skeleton rows.

---

### DiscoveryCard

```typescript
// src/components/home/DiscoveryCard.tsx
// Client component -- reads dismissed state from localStorage.
// Evaluates triggers in priority order and shows the highest-priority active one.
```

**Trigger evaluation:**

```typescript
type DiscoveryTrigger = {
  id: string
  condition: (state: WorkspaceDiscoveryState) => boolean
  title: string
  body: string
  action: { label: string; href: string }
  priority: number     // lower = higher priority
}

const TRIGGERS: DiscoveryTrigger[] = [
  {
    id: 'quota_warning',
    priority: 1,
    condition: s => (s.quotaUsagePct ?? 0) >= 80,
    title: 'Approaching your token limit',
    body: 'You are using {quotaUsagePct}% of your monthly token budget.',
    action: { label: 'Review usage', href: '/settings/billing' },
  },
  {
    id: 'brain_health_low',
    priority: 2,
    condition: s => s.brainHealthScore !== null && s.brainHealthScore < 60,
    title: 'Your brain needs a tidy',
    body: 'Health score: {brainHealthScore}/100. There are orphaned and stale nodes.',
    action: { label: 'Run health check', href: '/brain/health' },
  },
  {
    id: 'brain_discovery',
    priority: 3,
    condition: s => s.memoryCount >= 10 && !s.brainGraphVisited,
    title: 'Your agent has been remembering',
    body: 'It has built up {memoryCount} memories. See how they connect.',
    action: { label: 'Open brain graph', href: '/brain/graph' },
  },
  {
    id: 'skills_empty',
    priority: 4,
    condition: s => s.sessionCount >= 5 && s.skillCount === 0,
    title: 'Your agent has no reusable skills yet',
    body: 'After 5+ sessions, it is worth teaching it skills it can reuse.',
    action: { label: 'Add a skill', href: '/skills' },
  },
  {
    id: 'voice_not_provisioned',
    priority: 5,
    condition: s => !s.voiceProvisioned && s.workspaceAgeDays >= 30,
    title: 'Give your agent a phone number',
    body: 'Clients can call it directly. It answers, books, and reports back.',
    action: { label: 'Set up voice', href: '/voice' },
  },
  {
    id: 'playbook_suggestion',
    priority: 6,
    condition: s => s.completedTaskCount > 0 && s.playbookCount === 0,
    title: 'Turn a task into a playbook',
    body: 'You have completed tasks. Save one as a playbook to reuse it.',
    action: { label: 'See tasks', href: '/tasks' },
  },
]
```

**Discovery state API:**

```
GET /api/workspace/discovery-state
Response:
{
  quotaUsagePct: number | null,
  brainHealthScore: number | null,
  memoryCount: number,
  brainGraphVisited: boolean,      // tracked server-side on /brain/graph visit
  sessionCount: number,
  skillCount: number,
  completedTaskCount: number,
  playbookCount: number,
  voiceProvisioned: boolean,
  workspaceAgeDays: number,
}
```

This is a single lightweight endpoint that aggregates the counts needed for trigger
evaluation. It does not return full objects, only counts and booleans. Max response
time: 100ms (all counts are pre-computed or cheap queries).

**Dismissed state:** Stored in `localStorage` as:
```json
{ "keprix_discovery_dismissed": { "brain_discovery": 1751500000000, "skills_empty": ... } }
```
Key = trigger id, value = Unix timestamp of dismissal. A trigger is suppressed if
`Date.now() - dismissedAt < 30 * 24 * 60 * 60 * 1000` (30 days).

**Card layout:**

```
┌──────────────────────────────────────────────────────────────────┐
│  [title]                                              [x Dismiss] │
│  [body text with interpolated values]                             │
│  [Action button]                                                  │
└──────────────────────────────────────────────────────────────────┘
```

- Card background: slightly elevated from page background (`surface` color token)
- Left border accent: 3px, colored by priority:
  - Priority 1-2 (quota, health): amber
  - Priority 3-6 (discovery): cyan (accent color)
- Dismiss button: top-right, icon only (x), accessible label "Dismiss this suggestion"
- Clicking the action button marks the trigger as "acted on" server-side
  (`PATCH /api/workspace/discovery-state` with `{ triggerId, action: 'acted_on' }`)
  so it does not reappear even after localStorage is cleared

**No active triggers:** Card is not rendered. No placeholder, no "nothing to show here".
The page simply has two rows instead of three.

---

## Welcome empty state

Shown when `sessionCount === 0`. Replaces the two-column grid entirely.

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Good morning, [name].                                         │
│  Your agent is ready.                                          │
│                                                                │
│  [+ Start your first session]                                  │
│                                                                │
│  Not sure what to ask?                                         │
│                                                                │
│  "Help me draft a reply to a client email"                     │
│  "Summarise the documents I uploaded last week"                │
│  "Research the top borehole contractors in Accra"             │
│  "Set a reminder to follow up with James on Thursday"          │
│                                                                │
│  Each suggestion is a clickable chip that pre-fills the        │
│  new session input with that text.                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

The suggestion chips are not random. They are selected from a static list filtered by
the product surface:
- `aiva` surface: CRM, email, appointment, follow-up suggestions
- `abbis` surface: property, borehole, document, report suggestions
- `keprix` native: generic suggestions covering a wide range

Each chip is a `<button>` that navigates to `/sessions/new?prefill=[encoded text]`.

---

## QuotaBar (sidebar component, not home-specific)

Defined here because it is the only home-surface quota indicator.

```typescript
// src/components/nav/QuotaBar.tsx
// Rendered at the bottom of the left nav when quotaUsagePct >= 70
```

```
[%] Token usage  82%
████████████████░░░░
[Upgrade plan]
```

- Shows only when usage >= 70%. Below 70% the space is empty (no "you're doing fine" text).
- Percentage is LLM tokens in (the primary resource). Other resources visible in /admin/quotas.
- "Upgrade plan" links to `/settings/billing`
- Entire component re-fetches every 5 minutes via a background interval

---

## Page-level loading state

The home page uses skeleton loaders, not a full-page spinner. The page shell (nav,
greeting bar) renders immediately. Each widget fades in its skeleton, then the real
data, with no layout shift.

Skeleton rules:
- Skeleton lines use the `surface` color token at 60% opacity, pulsing animation
- Skeletons match the height of real content (no jumping when data loads)
- Maximum skeleton display time: 3 seconds. After 3s, show the error state for that
  widget if data has not arrived.

---

## Files to create

```
src/app/(home)/
  page.tsx                     - Home server component (data fetching, layout)

src/components/home/
  GreetingBar.tsx              - Time-aware greeting + start session CTA
  RecentSessionsWidget.tsx     - Recent sessions list with session cards
  SessionCard.tsx              - Individual session card (used here and in /sessions)
  BrainWidget.tsx              - Brain node counts, health score, graph link
  ActiveTasksWidget.tsx        - Running/queued tasks with 15s polling
  DiscoveryCard.tsx            - Priority-ordered contextual discovery prompt
  WelcomeEmptyState.tsx        - Zero-session welcome screen with suggestion chips
  HomePageSkeleton.tsx         - Full-page skeleton layout matching real layout

src/components/nav/
  QuotaBar.tsx                 - Sidebar quota usage bar (>= 70% usage)

src/app/api/workspace/
  discovery-state/route.ts     - GET discovery state aggregation endpoint
                                 PATCH mark trigger acted_on

migrations/
  add_discovery_state_table.py - Stores brainGraphVisited, trigger acted_on records
```

Modifications to existing files:
- `src/app/layout.tsx` -- mount `QuotaBar` at the bottom of the left nav shell
- `src/app/(brain)/graph/page.tsx` -- on mount, call
  `PATCH /api/workspace/discovery-state { triggerId: 'brain_discovery', action: 'acted_on' }`
  so the brain discovery trigger does not reappear after the user has visited the graph

---

## Acceptance criteria

- Home page renders in under 800ms on a warm server (data fetching is parallel, not sequential).
- If any single data fetch fails, only that widget shows an error state. The rest of
  the page renders normally.
- GreetingBar shows the correct time-based greeting relative to the user's timezone
  (read from workspace settings, not server timezone).
- SessionCard shows "View in brain" only when the session has at least one memory.
- ActiveTasksWidget stops polling when `document.visibilityState === 'hidden'` and
  resumes when the tab becomes visible again.
- DiscoveryCard shows the highest-priority active and non-dismissed trigger.
- A dismissed trigger does not reappear on page reload within the 30-day window.
- A trigger marked "acted_on" server-side does not reappear even after localStorage
  is cleared.
- The quota_warning trigger (priority 1) appears when `quotaUsagePct >= 80`, regardless
  of whether other triggers are active.
- The welcome empty state renders when `sessionCount === 0` and shows product-appropriate
  suggestion chips.
- Clicking a suggestion chip navigates to `/sessions/new` with the chip text pre-filled.
- QuotaBar appears in the left nav when token usage >= 70% and is absent when below 70%.
- Page has no layout shift between skeleton and real content (skeleton heights match).
- The home page is accessible: all interactive elements have focus states, all images
  have alt text, the discovery card dismiss button has an aria-label.

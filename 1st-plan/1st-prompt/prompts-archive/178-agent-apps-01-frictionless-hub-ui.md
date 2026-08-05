# Keprix Prompt 178: Agent Apps - Frictionless Hub UI

## Purpose

Replace the minimal `/agent-apps` page (hardcoded `hello-agent` runner) with a **sellable hub**:
browse installed apps, open app detail, run with the correct app selected, and guide new users
with empty states and recommended templates (cards only; catalog install ships in prompt **182**).

Read `prompts-archive/ref-177-agent-apps-product-architecture.md`. Requires prompt **67** baseline shipped.

---

## Dependencies

- `src/keprix/agent_apps/routes.py` (`GET /api/agent-apps`, `POST /{name}/run`)
- `frontend/src/components/agent-apps/AgentAppList.tsx`, `AgentAppRunner.tsx`
- `frontend/src/lib/agent-apps-api.ts`
- UI patterns: `frontend/src/app/(workspace)/builder/page.tsx` (template cards), `PageHeader`, MUI theme

---

## What to build

### 1. Route structure

| Route | File |
| --- | --- |
| `/agent-apps` | Hub: tabs **Installed** / **Discover** (Discover shows placeholder until 182) |
| `/agent-apps/[slug]` | App detail: run panel, metadata, recent runs placeholder |

Create:

```text
frontend/src/app/(workspace)/agent-apps/[slug]/page.tsx
frontend/src/components/agent-apps/AgentAppHub.tsx
frontend/src/components/agent-apps/AgentAppCard.tsx
frontend/src/components/agent-apps/AgentAppDetail.tsx
frontend/src/components/agent-apps/AgentAppEmptyState.tsx
```

Refactor `page.tsx` to render `AgentAppHub`.

### 2. App selection wiring (critical fix)

`AgentAppRunner` must accept `appName` prop from URL or list selection. Remove hardcoded
`hello-agent` default except as fallback when registry empty.

Flow:

1. User clicks card in `AgentAppList` -> navigate to `/agent-apps/{name}`.
2. Detail page loads manifest summary from API (extend list response or add `GET /{name}`).
3. Run button calls `runAgentApp(appName, input, context)`.

### 3. Backend: app detail endpoint

Add to `routes.py`:

```python
@router.get("/{app_name}")
async def get_agent_app(app_name: str, ...) -> dict[str, Any]:
    """Return manifest summary: name, version, display_name, description, category, inputs (if v2), required_env."""
```

Return 404 when not installed. Do not expose filesystem paths to non-admin users.

### 4. Hub UX requirements

**Installed tab**

- Grid of `AgentAppCard`: icon placeholder (first letter or category icon), `display_name`,
  one-line description, version badge, **Open** CTA.
- If zero apps: `AgentAppEmptyState` with:
  - Headline: "Install your first agent app"
  - Primary CTA: "Browse templates" (switches to Discover tab)
  - Secondary: "Upload app bundle" (links to `/agent-apps/install` shell; full flow in **181**)

**Discover tab (stub for 182)**

- Show 3 static recommendation cards (Daily Standup, Research Brief, Invoice Review) with
  **Coming soon** or disabled **Install** if catalog API not ready.
- Copy must set expectations: one-click install in next release.

**Run panel (detail page)**

- Text field for freeform input (until dynamic forms in **179**).
- **Run now** button with loading state and error alert.
- Output area: markdown render when response contains `output` or `markdown` key.
- Link: "View run history" (disabled until **185**).

### 5. Navigation

Add **Agent apps** under workspace nav (`frontend/src/lib/navigation.ts`):

- Group: **Automations** or **Build** (match existing sidebar conventions)
- Icon: `Apps` or `SmartToy`
- Path: `/agent-apps`

### 6. API client extensions

In `agent-apps-api.ts`:

```typescript
export async function getAgentApp(name: string): Promise<AgentAppDetail>;
export async function listAgentApps(): Promise<AgentAppSummary[]>;
```

Types: `AgentAppSummary`, `AgentAppDetail`, `AgentAppRunResult`.

---

## Acceptance criteria

- [ ] `/agent-apps` shows installed apps; clicking opens `/agent-apps/[slug]`.
- [ ] Run uses selected app name, not hardcoded `hello-agent`.
- [ ] `GET /api/agent-apps/{name}` returns manifest summary.
- [ ] Empty state guides user to Discover / upload.
- [ ] Nav link visible in workspace sidebar.
- [ ] No stubs: all buttons either work or show honest "available after install" copy.
- [ ] Responsive layout on mobile (single column cards).

---

## Tests

- `tests/agent_apps/test_routes.py`: `GET /{name}` 200/404
- Optional frontend: Vitest smoke for `AgentAppCard` render

---

## Out of scope (later prompts)

- Dynamic input forms (**179**)
- Zip upload (**181**)
- Catalog install API (**182**)
- Billing gates (**184**)

---

## Archive

On completion: move to `prompts-archive/` and update `PROMPT-IMPLEMENTATION-AUDIT.md`.

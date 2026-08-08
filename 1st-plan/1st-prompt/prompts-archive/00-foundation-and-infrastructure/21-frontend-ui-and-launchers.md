# keprix - Prompt 21: Frontend UI and Launchers

## Context

Sources:
- `carina/03-frontends/client-apps/app.carinaai.uk/` - Aiva (commercial) frontend (reference only)
- `hermes-agent/web/` - Hermes web dashboard
- `hermes-agent/ui-tui/` - Hermes TUI
- `odysseus/routes/` - Odysseus UI routes (gallery, themes, fonts)
- `odysseus/routes/gallery_routes.py`, `gallery_helpers.py` - gallery/image editor
Output: `keprix/frontend/`

## Primary Frontend

The keprix web frontend can learn from the Aiva commercial UI patterns, but it
must not become an Aiva fork. Build a standalone keprix workspace that talks to
the keprix Python backend.

### Step 1: Create the keprix Frontend

```
cd /opt/lampp/htdocs/verlox/keprix/keprix
pnpm create next-app frontend --ts --eslint --app --src-dir
```

Use Aiva only as visual reference for spacing, navigation density, and premium
business polish. Do not copy Aiva product routes, Aiva copy, Aiva billing flows,
or Aiva keys.

### Step 2: Exclude Commercial-only UI

Do not add the following components/pages:
- Aiva VA module
- Any page that imports from Scout client
- Billing or plan enforcement UI
- Scout security dashboard
- Any `requireTeamPlan` or `requireEnterprisePlan` middleware

Do NOT delete the layout, navigation, or any shared components.

### Step 3: Add keprix Pages

Add these pages that exist in keprix backend but not Enterprise frontend:

1. **`/playbook`** - Local Model Playbook
   - Hardware scan results + fit scores
   - Model grid with download/serve buttons
   - Serving dashboard (active local models + ports)
   - Based on Odysseus playbook UI patterns

2. **`/research`** - Deep Research
   - Query input with depth selector (quick/standard/deep)
   - Real-time progress (SSE stream)
   - Rendered report with citation links
   - Research history list

3. **`/compare`** - Blind Model Comparison
   - Split-pane: response A vs response B
   - Vote buttons (A wins, B wins, Tie)
   - Reveal model names after voting
   - Leaderboard tab

4. **`/email`** - Email Inbox
   - Account list sidebar
   - Email list with AI tags and priority indicators
   - Email reader with AI summary panel
   - Compose/reply/forward with AI draft button

5. **`/vault`** - Credentials Vault
   - Category-filtered item list
   - Add/edit/delete vault items
   - Master password unlock prompt
   - Search

6. **`/gallery`** - Image Gallery and Editor
   - Port Odysseus gallery UI patterns
   - Grid view of generated/uploaded images
   - Basic image editing (crop, filter, annotate)
   - `POST /api/workspace/gallery/upload` to add images

7. **`/admin/cron`** - Cron Job Manager
   - Job list with next-run countdown
   - Create job form: name, schedule (cron expression picker), prompt, output channel
   - Run now / disable / delete actions
   - Run history per job

8. **`/admin/mcp`** - MCP Server Manager
   - List configured MCP servers + status
   - Add server form (URL, name)
   - Per-server tool list
   - Connect/disconnect buttons

9. **`/admin/backup`** - Backup and Restore
   - Create backup button
   - Backup list with download links
   - Restore from file upload

### Step 4: Adapt API Calls

The Enterprise frontend calls `/api/aiva/*` and `/api/core/*` proxied to the Node.js
backend. keprix frontend calls the Python backend directly.

Create `frontend/src/lib/ce-api.ts`:
```typescript
// Base URL for keprix backend
const CE_API_BASE = process.env.NEXT_PUBLIC_CE_API_URL || 'http://localhost:3333';

export async function ceApi(path: string, options?: RequestInit) {
  const res = await fetch(`${CE_API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getCEToken()}`,
      ...options?.headers,
    },
  });
  return res;
}
```

Update all existing Enterprise API calls to use `ceApi()` instead of the
`handleAivaProxy` / Next.js route handler pattern.

### Step 5: Auth Adapter

The Enterprise frontend uses `better-auth` with cross-subdomain cookies.
keprix is single-domain (self-hosted). Replace the auth layer:

`frontend/src/lib/ce-auth.ts`:
- On login: call `POST /api/auth/login` on the Python backend
- Store bearer token in `localStorage` (or HttpOnly cookie if same-origin)
- `getCEToken()` reads token from storage
- `useCESession()` hook: returns `{ user, isLoading, signOut }`

Replace `better-auth` imports in all pages with `useCESession()`.

## Launchers

The keprix web UI must include launchers matching the Aiva (commercial) pattern.

`frontend/src/app/(workspace)/launcher/page.tsx` - main launcher:
- Grid of capability cards:
  - Chat (with model selector)
  - Deep Research
  - Documents
  - Notes
  - Tasks
  - Calendar
  - Email
  - Playbook
  - Compare Models
  - Gallery
  - Vault
  - Cron Jobs
  - MCP Servers
  - Skills Hub
  - Settings

Each card shows: icon, name, one-line description, quick-launch button.
On click: navigates to the feature page.

The launcher is the default landing page after login.

## Theme Support

From Odysseus `routes/prefs_routes.py` and the Keprix theme switcher CSS library:
- Light / Dark / System auto
- Port Hermes personality themes if applicable
- Theme stored in user preferences (DB) and `localStorage` for instant apply
- Use `/opt/lampp/htdocs/verlox/keprix/keprix/ui/theme-switcher-css/` as the
  primary reference for switcher CSS, theme variables, and named theme packs.

`frontend/src/app/api/themes/route.ts` - return available themes.
Theme CSS: import, adapt, or normalize from `keprix/ui/theme-switcher-css/`.
Do not copy Aiva commercial theme files into Keprix unless a file has already
been moved into this Keprix-owned theme library.

## Gallery / Image Editor UI

Port Odysseus gallery patterns to:
`frontend/src/app/(workspace)/gallery/page.tsx`:
- Upload images (drag+drop)
- Generate via image tool
- Grid view with click-to-open
- Basic editor: crop, rotate, brightness/contrast slider
- Download and delete

## TUI (Terminal UI)

Port `hermes-agent/ui-tui/` verbatim to `keprix/frontend/tui/`.
The TUI is a separate terminal interface (not the web UI) for power users.

```
ui-tui/packages/  -> frontend/tui/packages/
ui-tui/scripts/   -> frontend/tui/scripts/
ui-tui/src/       -> frontend/tui/src/
```

Command: `python -m keprix tui` starts the terminal UI.

## Desktop App (Electron)

Port `hermes-agent/apps/desktop/` to `keprix/frontend/desktop/`.
This is the Electron desktop app wrapping the web UI.
Command: `npm run desktop` in `frontend/desktop/`.

## Hermes Web Dashboard (superseded)

Do not port `hermes-agent/web/`. The Hermes web dashboard was dropped in favor of the
Next.js frontend (prompts 116-118, 136-137). Gateway status can surface in the admin shell.

## OpenClaw Canvas UI

OpenClaw has a Canvas (live structured output surface). In keprix, implement
a basic Canvas panel in the chat UI:
`frontend/src/components/chat/CanvasPanel.tsx`:
- Right-side panel that appears when agent outputs structured data
- Renders: tables (from markdown), code blocks with syntax highlighting,
  image outputs, Mermaid diagrams
- Collapsible, resizable

## Responsive Design

All new pages must be responsive:
- Mobile: single column, collapsible sidebar
- Tablet: two-column layout
- Desktop: three-column (sidebar + content + detail panel)

Follow the existing Aiva (commercial) CSS conventions (`text-text-primary`,
`bg-elevated`, `border-border`, etc.).

## Onboarding Wizard

First-run wizard for new keprix installations:
`frontend/src/app/onboarding/page.tsx` (multi-step):
1. Welcome to keprix
2. Set admin password (if not set via env)
3. Configure first LLM provider (API key input)
4. Configure messaging channel (Telegram bot token, optional)
5. Test the setup (send a test message)
6. Done - go to launcher

Skip steps where env vars already set.

## Acceptance Criteria

- `pnpm build` in `frontend/` succeeds without errors
- `pnpm dev` starts Next.js on port 3000; launcher page loads
- Login page submits to `POST /api/auth/login` on the Python backend
- `/research` page shows the query input and depth selector
- `/email` page renders (empty inbox acceptable if no account configured)
- `/playbook` page shows hardware scan button
- `/compare` page shows two response panes
- All pages responsive at 375px viewport width
- `grep -r "aiva.co.uk\|hireaiva" frontend/src/` returns zero matches
- `grep -r "requireTeamPlan\|requireEnterprisePlan" frontend/src/` returns zero matches

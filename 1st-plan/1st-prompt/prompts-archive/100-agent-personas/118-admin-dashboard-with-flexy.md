# Keprix - Prompt 105: Admin Dashboard Shell and Overview Page

## Context

Complete Prompts 103 and 103 first.

Sources:
- SaasAble admin shell: `planning/ui-references/saasable-ui/admin/nextjs/src/`
- Flexy dashboard components: `planning/ui-references/flexy-admin/package/src/`

Output: `keprix/frontend/src/app/(admin)/` and shared layout components.

The `(admin)` route group is for the Keprix instance owner. It shows operational
metrics: agent activity, tool usage, generated tool queue, memory store size,
active users, and channel health.

The `(workspace)` group (Prompt 136) shares the same layout shell but is
scoped to individual users interacting with the agent.

---

## Step 1: Sidebar

### Source files to port

From SaasAble admin:
```
admin/nextjs/src/layouts/AdminLayout/Drawer/           -> sidebar shell
admin/nextjs/src/layouts/AdminLayout/Drawer/DrawerContent/
admin/nextjs/src/layouts/AdminLayout/Drawer/DrawerHeader/
admin/nextjs/src/menu/index.jsx                        -> nav item definitions
```

From Flexy (richer sidebar implementation - use this in preference):
```
flexy: layout/sidebar/Sidebar.tsx      -> sidebar container
flexy: layout/sidebar/SidebarItems.tsx -> recursive nav item renderer
flexy: layout/sidebar/MenuItems.tsx    -> menu data definition
```

Port Flexy's sidebar because it handles nested items and active state better than
SaasAble's free version.

### Keprix sidebar nav items

Replace Flexy's `MenuItems.tsx` content with:

```typescript
export const ADMIN_NAV_ITEMS = [
  {
    title: 'Overview',
    href: '/dashboard',
    icon: 'IconLayoutDashboard',
  },
  {
    title: 'Agent',
    subheader: true,
  },
  {
    title: 'Conversations',
    href: '/dashboard/conversations',
    icon: 'IconMessages',
  },
  {
    title: 'Tool Library',
    href: '/dashboard/tools',
    icon: 'IconTools',
  },
  {
    title: 'Mutation Queue',
    href: '/dashboard/mutations',
    icon: 'IconGitBranch',
    badge: 'pendingMutations',  // dynamic count from API
  },
  {
    title: 'Memory Store',
    href: '/dashboard/memory',
    icon: 'IconDatabase',
  },
  {
    title: 'Instance',
    subheader: true,
  },
  {
    title: 'Channels',
    href: '/dashboard/channels',
    icon: 'IconBrandTelegram',
  },
  {
    title: 'API Keys',
    href: '/dashboard/keys',
    icon: 'IconKey',
  },
  {
    title: 'Users',
    href: '/dashboard/users',
    icon: 'IconUsers',
  },
  {
    title: 'Settings',
    href: '/dashboard/settings',
    icon: 'IconSettings',
  },
];
```

Use `@tabler/icons-react` for icons (already used by both templates).
Sidebar width: 260px expanded, 72px collapsed (icon-only).
Collapse toggle stored in localStorage.

File: `keprix/frontend/src/components/admin/Sidebar.tsx`

---

## Step 2: Top header bar

### Source files to port

From Flexy (richer implementation):
```
flexy: layout/header/Header.tsx       -> top bar container
flexy: layout/header/Topbar.tsx       -> inner content row
flexy: layout/header/Notification.tsx -> notification dropdown
flexy: layout/header/Profile.tsx      -> user profile dropdown
```

### Keprix header content

Left side: sidebar collapse toggle + breadcrumb.

Right side (left to right):
1. Global search (`/` keyboard shortcut opens command palette - implement in Prompt 137)
2. Notification bell - links to `/dashboard/mutations` when there are pending mutations
3. User avatar dropdown:
   - Display name + email
   - "View as user" toggle (switch to workspace view)
   - Settings
   - Sign out

Use `keprixTheme` MUI AppBar styles from Prompt 103 (glass blur effect).

File: `keprix/frontend/src/components/admin/AdminHeader.tsx`

---

## Step 3: Admin layout wrapper

Create `keprix/frontend/src/app/(admin)/layout.tsx`:

```typescript
import { AdminSidebar } from '@/components/admin/Sidebar';
import { AdminHeader }  from '@/components/admin/AdminHeader';
import { Box }          from '@mui/material';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AdminSidebar />
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <AdminHeader />
        <Box
          component="main"
          sx={{ flex: 1, p: 3, overflow: 'auto', bgcolor: 'background.default' }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
```

---

## Step 4: Stat card primitive

Create `keprix/frontend/src/components/admin/StatCard.tsx`:

```typescript
interface StatCardProps {
  title:    string;
  value:    string | number;
  delta?:   string; // e.g. "+12% vs last week"
  positive?: boolean; // green vs red delta
  icon:     React.ReactNode;
  color?:   'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
}
```

Card design: icon badge top-left, large value, small title below, delta badge bottom-right.
Use `DashboardCard` from Prompt 103 as the container.

---

## Step 5: Overview dashboard page

File: `keprix/frontend/src/app/(admin)/dashboard/page.tsx`

### Row 1: Stat cards (4 across on desktop, 2 on tablet, 1 on mobile)

| Card | Value source | Icon |
| --- | --- | --- |
| Total conversations | `GET /api/stats/conversations/count` | IconMessages |
| Active tools | `GET /api/stats/tools/count` | IconTools |
| Tools synthesised | `GET /api/stats/mutations/approved` | IconSparkles |
| Memory documents | `GET /api/stats/memory/count` | IconFiles |

### Row 2: Charts - port from Flexy

**Agent Activity chart** (left, 8/12 columns):

Port `flexy: components/dashboard/SalesOverview.tsx` as `AgentActivity.tsx`.
Replace the sales data with agent conversation volume over the last 30 days.
Area chart using ApexCharts. Data from `GET /api/stats/conversations/daily`.

Change: series name "Conversations", color `keprixTheme.palette.primary.main`.

**Tool Synthesis breakdown** (right, 4/12 columns):

Port `flexy: components/dashboard/YearlyBreakup.tsx` as `ToolSynthesisBreakup.tsx`.
Replace data with tool source breakdown:
- Synthesised (Mutation engine)
- Built-in (shipped with Keprix)
- Community (installed from registry)

Donut chart. Colors: primary, secondary, success.

### Row 3: Tables and activity

**Recent tool synthesis requests** (left, 8/12 columns):

Port `flexy: components/dashboard/ProductPerformance.tsx` as `RecentMutations.tsx`.
Table columns: Tool name | Status | Requested by | Requested at | Action.
Status chips: Pending (warning), Approved (success), Rejected (error).
"Action" column shows "Review" button linking to `/dashboard/mutations/[id]`.
Data from `GET /api/mutations?limit=5&sort=created_at:desc`.

**Daily agent activity** (right, 4/12 columns):

Port `flexy: components/dashboard/DailyActivity.tsx` as `RecentConversations.tsx`.
Timeline of last 5 conversations: avatar initial, session preview, time ago.
Data from `GET /api/conversations?limit=5&sort=created_at:desc`.

### Row 4: Channel health

Build from scratch (no template reference).

Horizontal card strip showing each configured channel's status:
- Channel icon + name
- Status dot: green (connected), amber (degraded), red (error)
- Last message timestamp
- "Configure" link

Data from `GET /api/channels/status`.

---

## Step 6: Auth pages

### Source to port

From SaasAble admin:
```
admin/nextjs/src/sections/auth/AuthLogin.jsx    -> port to login/LoginForm.tsx
admin/nextjs/src/sections/auth/AuthRegister.jsx -> port to register/RegisterForm.tsx
admin/nextjs/src/layouts/AuthLayout/            -> AuthLayout wrapper
```

### Login page

File: `keprix/frontend/src/app/auth/login/page.tsx`

Left panel: dark slate bg, `KeprixLogo` centered, tagline below:
"Your self-hosted AI agent. Running on your terms."

Right panel: white/paper card, `LoginForm` component.

Form fields: Email, Password, "Remember me" checkbox.
Submit: calls `NextAuth signIn('credentials', ...)`.
Below form: "First time? Set up your instance" link to `/auth/setup`.

### Setup page (first-run wizard)

File: `keprix/frontend/src/app/auth/setup/page.tsx`

Multi-step wizard. Steps:

```
Step 1: Welcome
  "You are setting up your Keprix instance."
  "This creates the owner (developer) account."
  [Continue]

Step 2: Owner account
  Full name, Email, Password, Confirm password.

Step 3: LLM provider
  Select primary LLM: Anthropic / OpenAI / Gemini / Groq / Ollama.
  API key input (masked). Test connection button.

Step 4: Done
  Instance fingerprint displayed.
  "Developer identity created at ~/.keprix/identity/dev.json"
  [Open dashboard]
```

POST each step's data to `POST /api/setup/step/{n}`.
The setup route is only accessible when `KEPRIX_SETUP_COMPLETE=false`.

---

## Acceptance Criteria

- Sidebar renders with all nine nav items and correct icons.
- Sidebar collapses to icon-only on toggle, state persists in localStorage.
- Header renders notification bell and profile dropdown.
- Dashboard page renders 4 stat cards, 2 charts (ApexCharts loaded), 1 table, 1 timeline.
- All chart data fetched from API (SWR hooks with loading skeletons).
- Channel health strip renders at least one row (mock data acceptable until Prompt 137).
- Login page renders split layout with `KeprixLogo` on left.
- Setup wizard renders all 4 steps and advances on form submit.
- `pnpm build` completes without error.
- No SaasAble or Flexy branding strings anywhere.

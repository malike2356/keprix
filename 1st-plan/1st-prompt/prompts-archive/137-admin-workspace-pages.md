# Keprix Prompt 137: Admin Workspace Pages

**Status:** Completed 2026-07-06. Evidence: `AdminTable`, users/models/mutations/usage/channels/settings pages, `/admin/billing`, `admin-nav.ts`.

## Purpose

Complete the non-dashboard admin pages so an operator can manage every aspect of their Keprix
instance from the web UI: user management, model/provider configuration, LLM usage with budget
controls, mutation (tool synthesis) review queue, channel management, and instance settings.

The admin layout and sidebar are already in place. This prompt delivers each page's data table,
forms, and actions.

---

## Dependencies

- `frontend/src/app/(admin)/layout.tsx` (exists)
- `frontend/src/components/admin/Sidebar.tsx` (exists)
- `frontend/src/components/admin/AdminHeader.tsx` (exists)
- `frontend/src/components/admin/ToolDetailDrawer.tsx` (exists, scaffold)
- `frontend/src/lib/admin-api.ts` (exists, fetch functions)
- `frontend/src/lib/admin-workspace-api.ts` (exists, scaffold)
- `frontend/src/lib/model-api.ts` (exists, scaffold)
- `frontend/src/lib/usage-api.ts` (exists, scaffold)
- `frontend/src/lib/billing-api.ts` (exists, scaffold)
- Prompt 118 complete (admin dashboard with StatCards and charts working)
- Prompt 116 complete (theme)

Backend endpoints used:
- `GET /api/admin/users`, `POST /api/admin/users`, `PATCH /api/admin/users/{id}`,
  `DELETE /api/admin/users/{id}`
- `GET /api/admin/models`, `POST /api/admin/models`, `PATCH /api/admin/models/{id}`,
  `DELETE /api/admin/models/{id}`
- `GET /api/admin/mutations`, `POST /api/mutations/{id}/approve`,
  `POST /api/mutations/{id}/reject`, `GET /api/mutations/{id}/code`
- `GET /api/admin/budget/status`, `PUT /api/admin/budget`,
  `GET /api/admin/usage/by-model`, `GET /api/admin/usage/daily`
- `GET /api/admin/channels`, `POST /api/admin/channels`, `PATCH /api/admin/channels/{id}`,
  `DELETE /api/admin/channels/{id}`
- `GET /api/admin/settings`, `PUT /api/admin/settings`

---

## What to build

### 1. Shared admin table wrapper

**`frontend/src/components/admin/AdminTable.tsx`** (NEW)

Reusable wrapper around MUI `Table` that adds a toolbar (title + action button), pagination,
and empty state.

```tsx
"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

type Column<T> = {
  id: keyof T | string;
  label: string;
  width?: number | string;
  render?: (row: T) => React.ReactNode;
};

type AdminTableProps<T extends { id: string }> = {
  title?: string;
  columns: Column<T>[];
  rows: T[];
  loading?: boolean;
  action?: React.ReactNode;
  page?: number;
  rowsPerPage?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onRowClick?: (row: T) => void;
};

export default function AdminTable<T extends { id: string }>({
  title,
  columns,
  rows,
  loading = false,
  action,
  page = 0,
  rowsPerPage = 25,
  total,
  onPageChange,
  onRowClick,
}: AdminTableProps<T>) {
  return (
    <Paper variant="outlined" sx={{ borderRadius: 2 }}>
      {(title || action) && (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", px: 2.5, py: 1.75 }}>
          {title ? <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>{title}</Typography> : <span />}
          {action}
        </Box>
      )}
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell key={String(col.id)} sx={{ fontWeight: 600, width: col.width }}>
                  {col.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((col) => (
                    <TableCell key={String(col.id)}>
                      <Box sx={{ height: 16, bgcolor: "divider", borderRadius: 0.5, width: "70%" }} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} sx={{ textAlign: "center", py: 4, color: "text.secondary" }}>
                  No records found.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow
                  key={row.id}
                  hover
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  sx={onRowClick ? { cursor: "pointer" } : undefined}
                >
                  {columns.map((col) => (
                    <TableCell key={String(col.id)}>
                      {col.render ? col.render(row) : String((row as Record<string, unknown>)[String(col.id)] ?? "")}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
      {total !== undefined && onPageChange ? (
        <TablePagination
          component="div"
          count={total}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={(_, p) => onPageChange(p)}
          rowsPerPageOptions={[]}
        />
      ) : null}
    </Paper>
  );
}
```

### 2. Users page

**`frontend/src/app/(admin)/users/page.tsx`** (NEW or EDIT)

Table of all users with invite and role-change actions.

```tsx
"use client";

import * as React from "react";
import useSWR from "swr";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import AdminTable from "@/components/admin/AdminTable";
import UserFormDialog from "@/components/admin/UserFormDialog";
import ConfirmDialog from "@/components/admin/ConfirmDialog";
import { ceApi } from "@/lib/ce-api";

type AdminUser = {
  id: string;
  username: string;
  email: string | null;
  role: "admin" | "member" | "viewer";
  created_at: string;
};

export default function UsersPage() {
  const { data, isLoading, mutate } = useSWR<AdminUser[]>("admin-users", async () => {
    const res = await ceApi("/api/admin/users");
    return res.json();
  });
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<AdminUser | null>(null);

  const columns = [
    { id: "username", label: "Username" },
    { id: "email", label: "Email" },
    {
      id: "role",
      label: "Role",
      render: (row: AdminUser) => (
        <Chip
          label={row.role}
          size="small"
          color={row.role === "admin" ? "primary" : "default"}
          variant="outlined"
        />
      ),
    },
    { id: "created_at", label: "Created", render: (row: AdminUser) => new Date(row.created_at).toLocaleDateString() },
    {
      id: "actions",
      label: "",
      width: 60,
      render: (row: AdminUser) => (
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); setDeleteTarget(row); }}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  return (
    <>
      <AdminTable
        title="Users"
        columns={columns}
        rows={data ?? []}
        loading={isLoading}
        action={
          <Button size="small" variant="contained" onClick={() => setDialogOpen(true)}>
            Invite user
          </Button>
        }
      />
      <UserFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSaved={() => { void mutate(); setDialogOpen(false); }}
      />
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete user"
        body={`Delete "${deleteTarget?.username}"? This cannot be undone.`}
        onConfirm={async () => {
          if (!deleteTarget) return;
          await ceApi(`/api/admin/users/${deleteTarget.id}`, { method: "DELETE" });
          void mutate();
          setDeleteTarget(null);
        }}
        onClose={() => setDeleteTarget(null)}
      />
    </>
  );
}
```

**`frontend/src/components/admin/UserFormDialog.tsx`** (NEW)

Dialog with fields: username (text), email (email, optional), role (select: admin/member/viewer),
password (text, for new users). Submit: `POST /api/admin/users`. Show Snackbar on success/error.

**`frontend/src/components/admin/ConfirmDialog.tsx`** (NEW)

Reusable confirmation dialog. Props: `open`, `title`, `body`, `onConfirm`, `onClose`.
Buttons: "Cancel" (outlined) and "Confirm" (contained, color="error" for destructive actions).

### 3. Models page

**`frontend/src/app/(admin)/models/page.tsx`** (NEW or EDIT)

Table of LLM provider configurations. Also a row for embed models.

Columns: Provider, Model ID, Type (chat/embed), Enabled (Switch), Priority, Actions (Delete).

"Add model" opens a Dialog:

```tsx
// Fields:
// - Provider: Select ["anthropic", "openai", "gemini", "groq", "ollama", "openrouter"]
// - Model ID: text (e.g. "claude-3-5-sonnet-20241022")
// - Type: Select ["chat", "embed"]
// - API key: password field (stored server-side, never returned in GET)
// - Input cost per 1M tokens: number
// - Output cost per 1M tokens: number
// - Enabled: checkbox (default true)
// Submit: POST /api/admin/models
```

On enable/disable toggle: optimistic update + `PATCH /api/admin/models/{id}` with `{ enabled: boolean }`.

### 4. Mutations review page

**`frontend/src/app/(admin)/mutations/page.tsx`** (NEW or EDIT)

Table of synthesised tools with a status filter tab bar.

```tsx
// Tabs: All | Staged (badge with count) | Approved | Rejected
// Default tab: Staged if stagedCount > 0, else All

// Columns: Tool name, Status, Workspace, Lines of code, Created, Actions
// Actions for "staged" rows: "Review" button (opens ToolDetailDrawer)
// Actions for all rows: "Delete" button

// ToolDetailDrawer (already scaffolded at components/admin/ToolDetailDrawer.tsx):
// - Drawer anchor="right", width 520
// - Header: tool name + status chip + close button
// - Body: scrollable pre block with the tool's Python code (fetched from GET /api/mutations/{id}/code)
// - Footer: Approve + Reject buttons (only for staged), calls
//   POST /api/mutations/{id}/approve or /reject
//   On success: close drawer, refetch mutations table
```

**`frontend/src/components/admin/ToolDetailDrawer.tsx`** (EDIT - fill in real content)

```tsx
// Fetch tool code: useSWR(`mutation-code-${id}`, () => ceApi(`/api/mutations/${id}/code`).then(r => r.json()))
// Show syntax-highlighted pre block (same monospace style as ToolCallBlock in Prompt 136)
// "Copy code" button: navigator.clipboard.writeText(code)
```

### 5. Usage page

**`frontend/src/app/(admin)/usage/page.tsx`** (NEW or EDIT)

Three-panel usage dashboard.

**Panel 1: Budget status card**
Fetches `GET /api/admin/budget/status`. Shows:
- Large spend number: "$X.XX / $Y.YY"
- Progress bar (MUI `LinearProgress`) colored: success below threshold, warning near it, error over.
- "Edit budget" button opens a Dialog with fields: monthly_budget_usd (number) and
  alert_threshold_percent (number 1-100). Submit: `PUT /api/admin/budget`.

**Panel 2: Cost by model (donut chart)**
Fetches `GET /api/admin/usage/by-model`. Each item: `{ model_id, total_cost_usd, token_count }`.
Renders an ApexCharts `donut` chart. Legend below shows model name + cost formatted with
`formatUsdCost()` from `@/lib/usage-format`.

```tsx
const series = rows.map((r) => r.total_cost_usd);
const labels = rows.map((r) => r.model_id);
const options: ApexCharts.ApexOptions = {
  chart: { type: "donut", background: "transparent" },
  labels,
  theme: { mode: theme.palette.mode },
  legend: { position: "bottom" },
  dataLabels: { enabled: false },
  plotOptions: { pie: { donut: { size: "65%" } } },
};
```

**Panel 3: Daily cost chart**
Same area chart pattern as `AgentActivity` (Prompt 118) but with cost (USD) on Y axis. Y axis
formatter: `(v) => "$" + v.toFixed(2)`.

### 6. Channels page

**`frontend/src/app/(admin)/channels/page.tsx`** (NEW or EDIT)

Table of connected channels. Columns: Type, Name, Status chip, Last event, Actions.

"Add channel" opens a multi-step Dialog:
- Step 1: Select channel type (Telegram, Discord, Slack, WhatsApp, Email, Webhook)
- Step 2: Type-specific fields (e.g. Telegram: bot token; Email: IMAP host/port/user/password)
- Submit: `POST /api/admin/channels`

Status chip colors match `ChannelHealthStrip` from Prompt 118 (healthy=success, error=error,
disconnected=text.disabled).

Row actions: "Reconnect" button for error/disconnected channels, "Delete" for all.

### 7. Settings page

**`frontend/src/app/(admin)/settings/page.tsx`** (NEW or EDIT)

Instance settings form. Organized in sections with MUI `Divider` between them.

```tsx
// Section 1: Instance
//   - Instance name (text)
//   - Default workspace ID (text)
//   - Max concurrent agents (number, 1-32)

// Section 2: Security
//   - Auth enabled (Switch) - when disabled, any request is treated as admin
//   - Session duration hours (number)
//   - Require 2FA (Switch)

// Section 3: Defaults
//   - Default LLM model (Select, options from models list)
//   - Default persona (Select: beacon, compass, codex, etc.)
//   - Max tokens per response (number)

// Section 4: Mutation Engine
//   - Mutation Engine enabled (Switch)
//   - Tool synthesis enabled (Switch)
//   - Auto-approve mutations (Switch, dangerous - show warning chip when enabled)
//   - Sandbox timeout seconds (number)

// Save button: PUT /api/admin/settings with the full settings object
// Show Snackbar on save success/error
```

### 8. Admin sidebar navigation

**`frontend/src/components/admin/admin-nav.ts`** (EDIT)

Ensure the nav items array includes all pages from this prompt:

```ts
export const ADMIN_NAV_ITEMS = [
  { label: "Dashboard", href: "/admin/dashboard", icon: "dashboard" },
  { label: "Conversations", href: "/admin/conversations", icon: "chat" },
  { label: "Mutations", href: "/admin/mutations", icon: "mutation", badgeKey: "staged" },
  { label: "Models", href: "/admin/models", icon: "model" },
  { label: "Usage", href: "/admin/usage", icon: "usage" },
  { label: "Users", href: "/admin/users", icon: "users" },
  { label: "Channels", href: "/admin/channels", icon: "channel" },
  { label: "Billing", href: "/admin/billing", icon: "billing" },
  { label: "Settings", href: "/admin/settings", icon: "settings" },
];
```

The `badgeKey: "staged"` tells the Sidebar to show a count badge using `mutationStats.staged`.

**`frontend/src/components/admin/Sidebar.tsx`** (EDIT)

Render a numeric badge on the "Mutations" nav item when `staged > 0`. Fetch `staged` count from
`useMutationStats()` (already in `mutation-api.ts`).

```tsx
// In the nav item rendering:
{item.badgeKey === "staged" && stagedCount > 0 ? (
  <Badge badgeContent={stagedCount} color="warning" sx={{ ml: "auto" }}>
    <span />
  </Badge>
) : null}
```

### 9. Shared utility: Snackbar feedback

**`frontend/src/components/ui/SnackbarFeedback.tsx`** (NEW if not exists)

Single-file Snackbar + hook pattern used by all admin forms.

```tsx
"use client";

import * as React from "react";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";

type FeedbackState = { message: string; severity: "success" | "error" | "info" };

export function useSnackbar() {
  const [state, setState] = React.useState<FeedbackState | null>(null);

  const show = React.useCallback((message: string, severity: FeedbackState["severity"] = "success") => {
    setState({ message, severity });
  }, []);

  const close = React.useCallback(() => setState(null), []);

  return { state, show, close };
}

export function SnackbarFeedback({
  state,
  onClose,
}: {
  state: FeedbackState | null;
  onClose: () => void;
}) {
  return (
    <Snackbar open={Boolean(state)} autoHideDuration={3500} onClose={onClose} anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
      <Alert onClose={onClose} severity={state?.severity ?? "info"} variant="filled" elevation={4}>
        {state?.message}
      </Alert>
    </Snackbar>
  );
}
```

Usage in every admin form dialog:
```tsx
const { state, show, close } = useSnackbar();
// In try/catch:
show("Saved successfully");
// or:
show("Failed to save. Check the API connection.", "error");
// Render:
<SnackbarFeedback state={state} onClose={close} />
```

### 10. Acceptance test (manual)

After implementing:

1. Navigate to `/admin/users`. Table loads with all users. "Invite user" dialog opens, fills, and
   submits without error. The new user appears after mutate().
2. Navigate to `/admin/models`. All configured models visible. Enable/disable toggle works (chip
   updates optimistically). "Add model" dialog submits and new model appears.
3. Navigate to `/admin/mutations`. Default tab is "Staged" when staged count > 0. "Review" button
   opens the drawer with Python code. "Approve" button updates status to approved.
4. Navigate to `/admin/usage`. Budget status card shows spend bar. Donut chart renders model
   breakdown. "Edit budget" dialog saves and the card updates.
5. Navigate to `/admin/channels`. At least one channel visible (or empty state). "Add channel"
   multi-step dialog flows through type selection and credential entry.
6. Navigate to `/admin/settings`. Form loads with current values. Change a setting and save.
   Snackbar appears confirming save.
7. The Mutations nav item in the sidebar shows a badge when staged > 0.
8. All pages show loading skeletons while data is fetching, not blank screens.
9. All forms show Snackbar feedback on success and error.

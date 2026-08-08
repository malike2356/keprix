"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  type ActorOverrideLimits,
  type ActorQuotaStatus,
  type ActorScopeType,
  type ProductQuotaUsage,
  fetchActorDenials,
  fetchActorQuota,
  fetchProductQuotas,
  fetchSchedulerStats,
  fetchUserQuotaStatus,
  formatCount,
  formatResourceLabel,
  putActorQuotaOverride,
  resetProductQuota,
  usagePercent,
} from "@/lib/quotas-api";

const SCOPE_TYPES: ActorScopeType[] = ["workspace", "user", "agent", "api_token", "product"];

const PRIMARY_RESOURCES = [
  "llm_tokens_in",
  "llm_tokens_out",
  "tool_calls",
  "api_calls",
  "mutation_runs",
  "estimated_tokens",
  "voice_minutes",
  "storage_bytes",
  "concurrent_sessions",
] as const;

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

function progressColor(pct: number | null): "primary" | "warning" | "error" | "success" {
  if (pct == null) return "primary";
  if (pct >= 90) return "error";
  if (pct >= 70) return "warning";
  return "success";
}

function ResourceBars({ usage }: { usage: ProductQuotaUsage }) {
  const usedMap = usage.usage || {};
  const limitMap = usage.limits || {};
  const keys = Array.from(
    new Set([...PRIMARY_RESOURCES, ...Object.keys(limitMap), ...Object.keys(usedMap)]),
  ).filter((key) => (limitMap[key] ?? 0) > 0 || (usedMap[key] ?? 0) > 0);

  if (keys.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No metered usage in this period yet. Limits are configured for this product.
      </Typography>
    );
  }

  return (
    <Stack spacing={1.25}>
      {keys.map((key) => {
        const used = usedMap[key] ?? 0;
        const limit = limitMap[key] ?? 0;
        const pct = usagePercent(used, limit);
        return (
          <Box key={key}>
            <Stack direction="row" justifyContent="space-between" spacing={1} sx={{ mb: 0.5 }}>
              <Typography variant="caption">{formatResourceLabel(key)}</Typography>
              <Typography variant="caption" color="text.secondary">
                {formatCount(used)} / {formatCount(limit || null)}
                {pct != null ? ` (${pct}%)` : ""}
              </Typography>
            </Stack>
            <LinearProgress
              variant="determinate"
              value={pct ?? 0}
              color={progressColor(pct)}
              sx={{ height: 6, borderRadius: 1 }}
            />
          </Box>
        );
      })}
    </Stack>
  );
}

function ActorStatusCard({ title, status }: { title: string; status?: ActorQuotaStatus | null }) {
  if (!status) return null;
  const usage = status.usage || {};
  const remaining = status.remaining || {};
  const limits = (status.limits || {}) as Record<string, number | string | undefined>;
  return (
    <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        {title}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
        Period: {status.period || "month"}
        {status.scope?.type ? ` · ${status.scope.type}:${status.scope.id}` : ""}
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Metric</TableCell>
            <TableCell align="right">Used</TableCell>
            <TableCell align="right">Limit</TableCell>
            <TableCell align="right">Remaining</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(
            [
              ["calls", usage.calls, limits.max_calls, remaining.calls],
              ["tokens", usage.tokens, limits.max_tokens, remaining.tokens],
              ["tool_runs", usage.tool_runs, limits.max_tool_runs, remaining.tool_runs],
              ["mutation_runs", usage.mutation_runs, limits.max_mutation_runs, remaining.mutation_runs],
            ] as const
          ).map(([label, used, limit, rem]) => (
            <TableRow key={label}>
              <TableCell>{formatResourceLabel(label)}</TableCell>
              <TableCell align="right">{formatCount(used ?? 0)}</TableCell>
              <TableCell align="right">{formatCount(typeof limit === "number" ? limit : null)}</TableCell>
              <TableCell align="right">{formatCount(typeof rem === "number" ? rem : null)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}

function ProductsPanel({
  onError,
  onMessage,
}: {
  onError: (msg: string | null) => void;
  onMessage: (msg: string | null) => void;
}) {
  const { data, error, isLoading, mutate } = useSWR("admin-product-quotas", fetchProductQuotas, {
    refreshInterval: 30_000,
  });
  const [resetTarget, setResetTarget] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (error) onError(error instanceof Error ? error.message : "Failed to load product quotas");
  }, [error, onError]);

  async function confirmReset() {
    if (!resetTarget) return;
    setBusy(true);
    onError(null);
    try {
      await resetProductQuota(resetTarget);
      onMessage(`Reset usage counters for product "${resetTarget}".`);
      setResetTarget(null);
      await mutate();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  if (isLoading) return <SkeletonTable rows={4} columns={4} />;

  const usages = data?.usages ?? [];
  if (usages.length === 0) {
    return (
      <EmptyState
        title="No product quotas registered"
        description="Products register limits from their keprix.yaml at startup. Enforcement stays active with unlimited defaults until a product registers."
      />
    );
  }

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
        <Chip size="small" label={`Tier: ${data?.deployment_tier || "unknown"}`} />
        <Typography variant="body2" color="text.secondary">
          {data?.note || "Product quotas are separate from managed AI billing credits."}
        </Typography>
      </Stack>

      {usages.map((row) => (
        <Paper key={row.product_id} variant="outlined" sx={{ p: 2 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            justifyContent="space-between"
            spacing={1}
            sx={{ mb: 1.5 }}
          >
            <Box>
              <Typography variant="h6" component="h2">
                {row.product_id}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Period {row.period_start ? new Date(row.period_start).toLocaleString() : "?"}
                {" → "}
                {row.period_end ? new Date(row.period_end).toLocaleString() : "?"}
              </Typography>
            </Box>
            <Button
              size="small"
              color="warning"
              variant="outlined"
              onClick={() => setResetTarget(row.product_id)}
            >
              Reset period usage
            </Button>
          </Stack>
          <ResourceBars usage={row} />
        </Paper>
      ))}

      <Dialog open={Boolean(resetTarget)} onClose={() => (!busy ? setResetTarget(null) : undefined)}>
        <DialogTitle>Reset quota period?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This clears usage counters for <strong>{resetTarget}</strong> in the current period.
            Limits stay the same. Enforcement continues immediately.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetTarget(null)} disabled={busy}>
            Cancel
          </Button>
          <Button color="warning" variant="contained" onClick={confirmReset} disabled={busy}>
            {busy ? "Resetting…" : "Reset"}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

function ActorPanel({
  onError,
  onMessage,
}: {
  onError: (msg: string | null) => void;
  onMessage: (msg: string | null) => void;
}) {
  const [scopeType, setScopeType] = React.useState<ActorScopeType>("workspace");
  const [scopeId, setScopeId] = React.useState("default");
  const [loadedKey, setLoadedKey] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<ActorQuotaStatus | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [form, setForm] = React.useState<ActorOverrideLimits>({
    period: "month",
    max_calls: undefined,
    max_tokens: undefined,
    max_tool_runs: undefined,
    max_mutation_runs: undefined,
  });

  async function loadScope() {
    const id = scopeId.trim();
    if (!id) {
      onError("Scope id is required");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const next = await fetchActorQuota(scopeType, id);
      setStatus(next);
      setLoadedKey(`${scopeType}:${id}`);
      const limits = (next.override || next.limits || {}) as ActorOverrideLimits;
      setForm({
        period: (limits.period as "day" | "month") || "month",
        max_calls: typeof limits.max_calls === "number" ? limits.max_calls : undefined,
        max_tokens: typeof limits.max_tokens === "number" ? limits.max_tokens : undefined,
        max_tool_runs: typeof limits.max_tool_runs === "number" ? limits.max_tool_runs : undefined,
        max_mutation_runs:
          typeof limits.max_mutation_runs === "number" ? limits.max_mutation_runs : undefined,
      });
      onMessage(`Loaded ${scopeType}:${id}`);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveOverride() {
    const id = scopeId.trim();
    if (!id) {
      onError("Scope id is required");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const payload: ActorOverrideLimits = { period: form.period || "month" };
      if (form.max_calls) payload.max_calls = Number(form.max_calls);
      if (form.max_tokens) payload.max_tokens = Number(form.max_tokens);
      if (form.max_tool_runs) payload.max_tool_runs = Number(form.max_tool_runs);
      if (form.max_mutation_runs) payload.max_mutation_runs = Number(form.max_mutation_runs);
      await putActorQuotaOverride(scopeType, id, payload);
      onMessage(`Saved override for ${scopeType}:${id}`);
      await loadScope();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Save failed");
      setBusy(false);
    }
  }

  async function clearOverride() {
    const id = scopeId.trim();
    if (!id) return;
    setBusy(true);
    onError(null);
    try {
      await putActorQuotaOverride(scopeType, id, null);
      onMessage(`Cleared override for ${scopeType}:${id}`);
      await loadScope();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Clear failed");
      setBusy(false);
    }
  }

  return (
    <Stack spacing={2}>
      <Alert severity="info">
        Actor quotas are separate from managed AI billing credits. Overrides apply to the selected
        workspace, user, agent, API token, or product scope.
      </Alert>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "flex-end" }}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel id="quota-scope-type">Scope type</InputLabel>
            <Select
              labelId="quota-scope-type"
              label="Scope type"
              value={scopeType}
              onChange={(e) => setScopeType(e.target.value as ActorScopeType)}
            >
              {SCOPE_TYPES.map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Scope id"
            value={scopeId}
            onChange={(e) => setScopeId(e.target.value)}
            sx={{ minWidth: 220 }}
          />
          <Button variant="contained" onClick={loadScope} disabled={busy}>
            Load
          </Button>
        </Stack>
      </Paper>

      {status && loadedKey ? (
        <>
          <ActorStatusCard title={`Effective status (${loadedKey})`} status={status} />
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
              Override limits
            </Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 1.5 }}>
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel id="quota-period">Period</InputLabel>
                <Select
                  labelId="quota-period"
                  label="Period"
                  value={form.period || "month"}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, period: e.target.value as "day" | "month" }))
                  }
                >
                  <MenuItem value="day">day</MenuItem>
                  <MenuItem value="month">month</MenuItem>
                </Select>
              </FormControl>
              {(
                [
                  ["max_calls", "Max calls"],
                  ["max_tokens", "Max tokens"],
                  ["max_tool_runs", "Max tool runs"],
                  ["max_mutation_runs", "Max mutation runs"],
                ] as const
              ).map(([key, label]) => (
                <TextField
                  key={key}
                  size="small"
                  type="number"
                  label={label}
                  value={form[key] ?? ""}
                  onChange={(e) => {
                    const raw = e.target.value;
                    setForm((prev) => ({
                      ...prev,
                      [key]: raw === "" ? undefined : Number(raw),
                    }));
                  }}
                  inputProps={{ min: 1 }}
                />
              ))}
            </Stack>
            <Stack direction="row" spacing={1}>
              <Button variant="contained" onClick={saveOverride} disabled={busy}>
                Save override
              </Button>
              <Button color="warning" variant="outlined" onClick={clearOverride} disabled={busy}>
                Clear override
              </Button>
            </Stack>
            {status.override ? (
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Active override present for this scope.
              </Typography>
            ) : (
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                No override stored; default policy applies.
              </Typography>
            )}
          </Paper>
        </>
      ) : null}
    </Stack>
  );
}

function DenialsPanel({ onError }: { onError: (msg: string | null) => void }) {
  const { data, error, isLoading } = useSWR("admin-quota-denials", () => fetchActorDenials(50), {
    refreshInterval: 20_000,
  });

  React.useEffect(() => {
    if (error) onError(error instanceof Error ? error.message : "Failed to load denials");
  }, [error, onError]);

  if (isLoading) return <SkeletonTable rows={5} columns={6} />;

  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <EmptyState
        title="No recent denials"
        description="When an actor hits a hard limit, denials appear here with scope, metric, and reason."
      />
    );
  }

  return (
    <Paper variant="outlined" sx={{ overflow: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>When</TableCell>
            <TableCell>Scope</TableCell>
            <TableCell>Metric</TableCell>
            <TableCell>Service</TableCell>
            <TableCell>Reason</TableCell>
            <TableCell>Workspace</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((row, idx) => (
            <TableRow key={row.id ?? idx}>
              <TableCell>
                {row.created_at ? new Date(row.created_at).toLocaleString() : ";"}
              </TableCell>
              <TableCell>
                {row.scope_type}:{row.scope_id}
              </TableCell>
              <TableCell>{row.metric || ";"}</TableCell>
              <TableCell>{row.service || ";"}</TableCell>
              <TableCell>{row.reason || ";"}</TableCell>
              <TableCell>{row.workspace_id || ";"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}

function SchedulerPanel({ onError }: { onError: (msg: string | null) => void }) {
  const { data, error, isLoading } = useSWR("admin-quota-scheduler", fetchSchedulerStats, {
    refreshInterval: 10_000,
  });

  React.useEffect(() => {
    if (error) onError(error instanceof Error ? error.message : "Failed to load scheduler");
  }, [error, onError]);

  if (isLoading) return <SkeletonList rows={3} rowHeight={48} />;
  if (!data) {
    return <EmptyState title="Scheduler unavailable" description="Could not load fairness scheduler stats." />;
  }

  const util =
    data.max_slots > 0 ? Math.min(100, Math.round((data.active_slots / data.max_slots) * 100)) : 0;
  const perProduct = Object.entries(data.per_product || {});

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Fairness scheduler
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Weighted fair-share slots for concurrent LLM calls across products.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 1.5 }}>
          <Chip label={`Active ${data.active_slots} / ${data.max_slots}`} />
          <Chip label={`Queued ${data.queued_requests}`} variant="outlined" />
          <Chip label={`Utilisation ${util}%`} color={progressColor(util)} variant="outlined" />
        </Stack>
        <LinearProgress
          variant="determinate"
          value={util}
          color={progressColor(util)}
          sx={{ height: 8, borderRadius: 1 }}
        />
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Slots by product
        </Typography>
        {perProduct.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No product currently holds a scheduler slot.
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Product</TableCell>
                <TableCell align="right">Active slots</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {perProduct.map(([productId, slots]) => (
                <TableRow key={productId}>
                  <TableCell>{productId}</TableCell>
                  <TableCell align="right">{slots}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
}

export default function AdminQuotasPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [tab, setTab] = React.useState(0);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const myStatus = useSWR(isAdmin ? "my-quota-status" : null, fetchUserQuotaStatus);

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Quotas" description="Per-workspace usage quotas and rate limits." />
        <SkeletonList rows={4} rowHeight={48} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Quotas"
          description="Per-workspace usage quotas and rate limits."
          breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Quotas" }]}
        />
        <Alert severity="error">
          Admin role required. Your role ({user?.role || "unknown"}) cannot manage quotas.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Quotas"
        description="Per-workspace usage quotas and rate limits. Product quotas and actor quotas are separate from managed AI billing credits."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Quotas" }]}
        actions={
          <Button component={NextLink} href="/settings/billing" variant="outlined" size="small">
            Billing
          </Button>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
        <Box sx={{ flex: 1 }}>
          <ActorStatusCard title="Your user quota" status={myStatus.data?.user} />
        </Box>
        <Box sx={{ flex: 1 }}>
          <ActorStatusCard title="Active workspace quota" status={myStatus.data?.workspace} />
        </Box>
      </Stack>

      <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Products" />
        <Tab label="Actor overrides" />
        <Tab label="Denials" />
        <Tab label="Scheduler" />
      </Tabs>

      {tab === 0 ? <ProductsPanel onError={setError} onMessage={setMessage} /> : null}
      {tab === 1 ? <ActorPanel onError={setError} onMessage={setMessage} /> : null}
      {tab === 2 ? <DenialsPanel onError={setError} /> : null}
      {tab === 3 ? <SchedulerPanel onError={setError} /> : null}
    </Box>
  );
}

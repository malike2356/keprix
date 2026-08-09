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
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonList } from "@/components/ui/loading";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";
import { useCESession } from "@/lib/ce-auth";

type HotCachePayload = {
  enabled: boolean;
  path: string;
  content: string;
  [key: string]: unknown;
};

async function fetchHotCache(workspaceId: string) {
  const response = await ceApi(`/api/workspaces/${encodeURIComponent(workspaceId)}/hot-cache`);
  if (!response.ok) {
    throw new Error(parseApiErrorMessage(await response.json().catch(() => ({})), "Failed to load hot cache"));
  }
  return response.json() as Promise<HotCachePayload>;
}

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

export default function WorkspaceOpsPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [workspaceId, setWorkspaceId] = React.useState(
    () => String(user?.workspace_id || user?.active_workspace_id || "default"),
  );
  const [tab, setTab] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [confirmFlush, setConfirmFlush] = React.useState(false);

  React.useEffect(() => {
    const fromSession = String(user?.workspace_id || user?.active_workspace_id || "").trim();
    if (fromSession) setWorkspaceId(fromSession);
  }, [user?.workspace_id, user?.active_workspace_id]);

  const cache = useSWR(isAdmin && workspaceId ? ["hot-cache", workspaceId] : null, () =>
    fetchHotCache(workspaceId.trim() || "default"),
  );

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Workspace ops" description="Hot-cache and workspace operator tools." />
        <SkeletonList rows={4} rowHeight={48} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Workspace ops"
          description="Hot-cache and workspace operator tools."
          breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Workspace ops" }]}
        />
        <Alert severity="error">Admin role required.</Alert>
      </Box>
    );
  }

  async function toggleEnabled() {
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi(`/api/workspaces/${encodeURIComponent(workspaceId)}/hot-cache/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !(cache.data?.enabled) }),
      });
      if (!response.ok) {
        throw new Error(parseApiErrorMessage(await response.json().catch(() => ({})), "Config update failed"));
      }
      setMessage(`Hot cache ${cache.data?.enabled ? "disabled" : "enabled"} for ${workspaceId}.`);
      await cache.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Config failed");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCache() {
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi(`/api/workspaces/${encodeURIComponent(workspaceId)}/hot-cache/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force: true, summary: "operator refresh" }),
      });
      if (!response.ok) {
        throw new Error(parseApiErrorMessage(await response.json().catch(() => ({})), "Refresh failed"));
      }
      setMessage("Hot cache refreshed.");
      await cache.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setBusy(false);
    }
  }

  async function flushCache() {
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi(`/api/workspaces/${encodeURIComponent(workspaceId)}/hot-cache/flush`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!response.ok) {
        throw new Error(parseApiErrorMessage(await response.json().catch(() => ({})), "Flush failed"));
      }
      setMessage("Hot cache flushed.");
      setConfirmFlush(false);
      await cache.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Flush failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      <PageHeader
        title="Workspace ops"
        description="Hot-cache status, Soft Wall flush, and operator shortcuts for the selected workspace."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Workspace ops" }]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component="a" href="/workspace/new" size="small" variant="outlined">
              New workspace
            </Button>
            <Button component="a" href="/tenants" size="small" variant="outlined">
              Tenants
            </Button>
          </Stack>
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

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }} alignItems={{ sm: "center" }}>
        <TextField
          size="small"
          label="Workspace id"
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
        />
        <Button onClick={() => void cache.mutate()} disabled={busy}>
          Refresh status
        </Button>
        <Chip size="small" label={`workspace: ${workspaceId || "default"}`} variant="outlined" />
      </Stack>

      <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Hot cache" />
        <Tab label="Quick links" />
      </Tabs>

      {tab === 0 ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1">Hot cache</Typography>
            <Chip
              size="small"
              label={cache.data?.enabled ? "enabled" : "disabled"}
              color={cache.data?.enabled ? "success" : "default"}
              variant="outlined"
            />
          </Stack>

          {cache.error ? (
            <Alert severity="warning" sx={{ mt: 1 }}>
              Could not load hot cache ({cache.error.message}).
            </Alert>
          ) : cache.isLoading ? (
            <SkeletonList rows={3} rowHeight={40} />
          ) : (
            <>
              <Typography variant="body2" sx={{ mb: 0.5 }}>
                Path: {cache.data?.path || ";"}
              </Typography>
              {!cache.data?.enabled ? (
                <Alert severity="info" sx={{ my: 1 }}>
                  Hot cache is disabled for this workspace (honest no-op until enabled).
                </Alert>
              ) : null}

              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                Cache payload
              </Typography>
              {cache.data?.content ? (
                <Box
                  component="pre"
                  sx={{
                    m: 0,
                    p: 1.5,
                    maxHeight: 280,
                    overflow: "auto",
                    bgcolor: "action.hover",
                    borderRadius: 1,
                    fontSize: 12,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {cache.data.content}
                </Box>
              ) : (
                <EmptyState
                  title="No hot cache content"
                  description="Refresh to generate wiki/hot.md content, or enable the cache first."
                />
              )}

              <Box sx={{ mt: 1 }}>
                <StructuredDataView value={cache.data ?? {}} emptyLabel="(empty)" />
              </Box>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 2 }}>
                <Button disabled={busy} variant="outlined" onClick={() => void toggleEnabled()}>
                  {cache.data?.enabled ? "Disable cache" : "Enable cache"}
                </Button>
                <Button disabled={busy} variant="contained" onClick={() => void refreshCache()}>
                  Refresh cache
                </Button>
                <Button color="error" disabled={busy} onClick={() => setConfirmFlush(true)}>
                  Soft Wall flush
                </Button>
              </Stack>
            </>
          )}
        </Paper>
      ) : null}

      {tab === 1 ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Operator shortcuts
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Common admin destinations for the active workspace. These do not change workspace state by themselves.
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button component="a" href="/admin/readiness" size="small" variant="outlined">
              Readiness
            </Button>
            <Button component="a" href="/admin/quotas" size="small" variant="outlined">
              Quotas
            </Button>
            <Button component="a" href="/admin/feature-flags" size="small" variant="outlined">
              Feature flags
            </Button>
            <Button component="a" href="/admin/network-egress" size="small" variant="outlined">
              Network egress
            </Button>
            <Button component="a" href="/settings/users" size="small" variant="outlined">
              Users
            </Button>
            <Button component="a" href="/home" size="small" variant="outlined">
              Workspace home
            </Button>
          </Stack>
        </Paper>
      ) : null}

      <Dialog open={confirmFlush} onClose={() => (!busy ? setConfirmFlush(false) : undefined)}>
        <DialogTitle>Flush hot cache?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Soft Wall confirm: delete wiki/hot.md content for workspace <strong>{workspaceId}</strong>. This cannot be
            undone from this dialog.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmFlush(false)} disabled={busy}>
            Cancel
          </Button>
          <Button color="error" variant="contained" disabled={busy} onClick={() => void flushCache()}>
            {busy ? "Flushing…" : "Flush"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

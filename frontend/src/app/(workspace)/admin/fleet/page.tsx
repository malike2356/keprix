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
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import { fetchEdition, isFeatureEnabled } from "@/lib/edition";
import {
  fetchFleetAudit,
  fetchFleetInstances,
  isEnterpriseRequiredError,
  probeFleetInstance,
  registerFleetInstance,
  removeFleetInstance,
  type FleetInstance,
} from "@/lib/fleet-api";

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

function statusColor(status: string): "success" | "warning" | "error" | "info" | "default" {
  switch (status) {
    case "healthy":
      return "success";
    case "degraded":
    case "update_available":
      return "warning";
    case "unreachable":
      return "error";
    default:
      return "default";
  }
}

export default function FleetAdminPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [name, setName] = React.useState("");
  const [baseUrl, setBaseUrl] = React.useState("");
  const [version, setVersion] = React.useState("0.0.0");
  const [busy, setBusy] = React.useState(false);
  const [removeTarget, setRemoveTarget] = React.useState<FleetInstance | null>(null);

  const edition = useSWR(isAdmin ? "edition-fleet" : null, fetchEdition);
  const fleetEnabled = isFeatureEnabled(edition.data, "fleet_deploy");

  const instances = useSWR(
    isAdmin && fleetEnabled ? "fleet-instances" : null,
    fetchFleetInstances,
  );
  const audit = useSWR(
    isAdmin && fleetEnabled && isFeatureEnabled(edition.data, "audit_export")
      ? "fleet-audit"
      : null,
    () => fetchFleetAudit(40),
  );

  React.useEffect(() => {
    if (instances.error && isEnterpriseRequiredError(instances.error)) {
      setError(null);
    }
  }, [instances.error]);

  if (sessionLoading || edition.isLoading) {
    return (
      <Box>
        <PageHeader title="Fleet" description="Enterprise instance register and health." />
        <SkeletonTable rows={4} columns={6} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader title="Fleet" description="Enterprise instance register and health." />
        <Alert severity="error">Admin role required to manage the fleet.</Alert>
      </Box>
    );
  }

  if (edition.error) {
    return (
      <Box>
        <PageHeader title="Fleet" description="Enterprise instance register and health." />
        <Alert severity="error">Could not load edition features.</Alert>
      </Box>
    );
  }

  if (!fleetEnabled) {
    return (
      <Box>
        <PageHeader title="Fleet" description="Enterprise instance register and health." />
        <EmptyState
          title="Enterprise feature"
          description="Fleet deploy is available in Enterprise Edition. Community builds keep this surface locked so operators do not see fake instance data."
        />
        <Box sx={{ mt: 2, textAlign: "center" }}>
          <Button component="a" href="/settings/upgrade" variant="contained">
            View upgrades
          </Button>
        </Box>
      </Box>
    );
  }

  const rows = instances.data?.instances ?? [];

  async function onRegister() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await registerFleetInstance({
        name: name.trim(),
        base_url: baseUrl.trim(),
        version: version.trim() || "0.0.0",
      });
      setName("");
      setBaseUrl("");
      setVersion("0.0.0");
      setMessage("Instance registered.");
      await instances.mutate();
      await audit.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Register failed");
    } finally {
      setBusy(false);
    }
  }

  async function onProbe(id: string) {
    setBusy(true);
    setError(null);
    try {
      await probeFleetInstance(id);
      setMessage("Health refreshed.");
      await instances.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Probe failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmRemove() {
    if (!removeTarget) return;
    setBusy(true);
    setError(null);
    try {
      await removeFleetInstance(removeTarget.id);
      setMessage(`Removed ${removeTarget.name}.`);
      setRemoveTarget(null);
      await instances.mutate();
      await audit.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Remove failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      <PageHeader
        title="Fleet"
        description="Register managed Keprix instances, refresh health, and review alerts."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Fleet" }]}
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

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Register instance
        </Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems="flex-start">
          <TextField
            size="small"
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            sx={{ minWidth: 160 }}
          />
          <TextField
            size="small"
            label="Base URL"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://keprix.example.com"
            sx={{ flex: 1, minWidth: 240 }}
          />
          <TextField
            size="small"
            label="Version"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            sx={{ width: 120 }}
          />
          <Button
            variant="contained"
            disabled={busy || !name.trim() || !baseUrl.trim()}
            onClick={() => void onRegister()}
          >
            Register
          </Button>
        </Stack>
      </Paper>

      {instances.isLoading ? (
        <SkeletonTable rows={4} columns={6} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No fleet instances"
          description="Register a managed Keprix base URL to track health and alerts."
        />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Base URL</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Health</TableCell>
              <TableCell>Alerts</TableCell>
              <TableCell>Last seen</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.name}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ wordBreak: "break-all" }}>
                    {row.base_url}
                  </Typography>
                </TableCell>
                <TableCell>{row.version}</TableCell>
                <TableCell>
                  <Chip size="small" label={row.status} color={statusColor(row.status)} />
                </TableCell>
                <TableCell>{row.alerts ?? 0}</TableCell>
                <TableCell>{row.last_seen_at || "-"}</TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button size="small" disabled={busy} onClick={() => void onProbe(row.id)}>
                      Refresh health
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      disabled={busy}
                      onClick={() => setRemoveTarget(row)}
                    >
                      Remove
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {audit.data?.events?.length ? (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Recent audit
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>When</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Payload</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {audit.data.events.slice(0, 20).map((ev, idx) => (
                <TableRow key={`${ev.at}-${idx}`}>
                  <TableCell>{ev.at}</TableCell>
                  <TableCell>{ev.action}</TableCell>
                  <TableCell>
                    <StructuredDataView value={ev.payload || {}} dense />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : null}

      <Dialog open={Boolean(removeTarget)} onClose={() => setRemoveTarget(null)}>
        <DialogTitle>Remove fleet instance?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Soft Wall confirm: remove {removeTarget?.name} ({removeTarget?.base_url}) from the
            fleet register. This does not shut down the remote instance.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemoveTarget(null)}>Cancel</Button>
          <Button color="error" variant="contained" disabled={busy} onClick={() => void onConfirmRemove()}>
            Remove
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

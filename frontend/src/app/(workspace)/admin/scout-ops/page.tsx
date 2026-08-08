"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  activateScoutKill,
  fetchScoutKillStatus,
  fetchScoutSensors,
  resumeScoutKill,
} from "@/lib/scout-ops-api";

export default function ScoutOpsPage() {
  const workspaceId = "default";
  const [reason, setReason] = React.useState("Operator pause from Keprix Web UI");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const status = useSWR(["scout-kill-status", workspaceId], () => fetchScoutKillStatus(workspaceId), {
    refreshInterval: 10_000,
  });
  const sensors = useSWR("scout-sensors", fetchScoutSensors);

  const onKill = async () => {
    setBusy(true);
    setError(null);
    try {
      await activateScoutKill({ workspaceId, reason: reason.trim() });
      await status.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kill failed");
    } finally {
      setBusy(false);
    }
  };

  const onResume = async () => {
    setBusy(true);
    setError(null);
    try {
      await resumeScoutKill(workspaceId);
      await status.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Scout kill & sensors"
        description="Standalone operator controls for agent kill switch and Scout sensor catalog. Distinct from Scout Warden URL scans."
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      {status.error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {status.error.message}
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Kill switch
          </Typography>
          <Alert severity={status.data?.active ? "warning" : "success"} sx={{ mb: 2 }}>
            {status.data?.active
              ? `ACTIVE (${status.data.scope || "unknown"}): ${status.data.reason || "paused"}`
              : "Agents are running (no active kill for this workspace)."}
          </Alert>
          <TextField
            size="small"
            fullWidth
            label="Kill reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            sx={{ mb: 1 }}
          />
          <Stack direction="row" spacing={1}>
            <Button color="error" variant="contained" disabled={busy} onClick={() => void onKill()}>
              Activate kill
            </Button>
            <Button variant="outlined" disabled={busy} onClick={() => void onResume()}>
              Resume
            </Button>
            <Button size="small" onClick={() => void status.mutate()}>
              Refresh
            </Button>
          </Stack>
          {status.data?.active_kills && status.data.active_kills.length > 0 ? (
            <Box sx={{ mt: 2 }}>
              <StructuredDataView value={status.data.active_kills} />
            </Box>
          ) : null}
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Sensor catalog ({sensors.data?.sensors?.length ?? 0})
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Sensors Scout can register against this Keprix instance.
          </Typography>
          <Box sx={{ maxHeight: 360, overflow: "auto" }}>
            <StructuredDataView value={sensors.data?.sensors ?? status.data?.sensors ?? []} />
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

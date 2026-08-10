"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { IconAlertTriangle, IconPlayerPlay, IconRefresh } from "@tabler/icons-react";
import * as React from "react";
import PageContainer from "@/components/shared/PageContainer";
import BlankCard from "@/components/cards/BlankCard";
import { fetchKeprixHealth, restartKeprixEngine } from "@/lib/admin-workspace-api";

type EngineState = "checking" | "ready" | "restarting" | "offline" | "error";

export default function EngineControlPage() {
  const [state, setState] = React.useState<EngineState>("checking");
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const checkHealth = React.useCallback(async () => {
    try {
      const health = await fetchKeprixHealth();
      setState(health.status === "ok" ? "ready" : "error");
      return health.status === "ok";
    } catch {
      setState("offline");
      return false;
    }
  }, []);

  React.useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  const restart = async () => {
    if (!window.confirm("Restart the Keprix engine now? Active requests may be interrupted.")) return;
    setBusy(true);
    setState("restarting");
    setMessage("Restart requested. Waiting for Keprix to become healthy again...");
    try {
      await restartKeprixEngine();
      const started = Date.now();
      let healthy = false;
      while (!healthy && Date.now() - started < 60_000) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        healthy = await checkHealth();
      }
      if (healthy) setMessage("Keprix is healthy and ready.");
      else setMessage("Keprix has not reported healthy yet. Refresh this page or check Diagnostics.");
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Could not restart Keprix.");
    } finally {
      setBusy(false);
    }
  };

  const statusLabel = state === "ready" ? "Ready" : state === "restarting" ? "Restarting" : state === "offline" ? "Offline" : state === "checking" ? "Checking" : "Needs attention";
  const statusColor = state === "ready" ? "success" : state === "restarting" || state === "checking" ? "warning" : "error";

  return (
    <PageContainer title="Engine control" description="Restart and verify the Keprix AI engine." padded={false}>
      <Box sx={{ display: "grid", gap: 2, maxWidth: 760 }}>
        <Alert severity="info" icon={<IconPlayerPlay size={20} />}>
          This is the quickest place to recover the Keprix engine. Restarting affects new requests briefly, but does not delete workspace data, memory, documents, or Telegram configuration.
        </Alert>
        <BlankCard>
          <Box sx={{ p: { xs: 2, md: 3 }, display: "grid", gap: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>Keprix AI engine</Typography>
                <Typography variant="body2" color="text.secondary">The model and agent runtime used by Aiva.</Typography>
              </Box>
              <Chip label={statusLabel} color={statusColor} icon={state === "restarting" ? <CircularProgress size={14} /> : undefined} />
            </Box>
            {message ? <Alert severity={state === "error" || state === "offline" ? "warning" : "success"}>{message}</Alert> : null}
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Button variant="contained" color="warning" startIcon={busy ? <CircularProgress size={16} color="inherit" /> : <IconRefresh size={18} />} disabled={busy} onClick={() => void restart()}>
                {busy ? "Restarting..." : "Restart Keprix engine"}
              </Button>
              <Button variant="outlined" startIcon={<IconAlertTriangle size={18} />} disabled={busy} onClick={() => void checkHealth()}>
                Check health
              </Button>
            </Box>
          </Box>
        </BlankCard>
      </Box>
    </PageContainer>
  );
}

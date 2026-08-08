"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function fetchProxyStatus() {
  const response = await ceApi("/api/admin/proxy/status");
  if (!response.ok) throw new Error(parseApiErrorMessage(await response.json().catch(() => ({})), "Failed to load proxy status"));
  return response.json();
}

export default function ProxyOpsPanel() {
  const status = useSWR("proxy-ops-status", fetchProxyStatus);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState<boolean | null>(null);

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6">Credential proxy ops</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Doctor summary and Soft Wall cordon. Secrets never shown (last4/metadata only via vault UI).
      </Typography>
      {error ? <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert> : null}
      {message ? <Alert severity="success" sx={{ mb: 1 }}>{message}</Alert> : null}
      {status.error ? <Alert severity="warning">Proxy status unavailable: {status.error.message}</Alert> : null}
      <StructuredDataView value={status.data || {}} />
      <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
        <Button size="small" disabled={busy} onClick={() => void status.mutate()}>Refresh</Button>
        <Button
          size="small"
          disabled={busy}
          onClick={async () => {
            setBusy(true); setError(null);
            try {
              const response = await ceApi("/api/admin/proxy/doctor", { method: "POST" });
              if (!response.ok) throw new Error("Doctor failed");
              setMessage("Doctor finished");
              await status.mutate();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Doctor failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          Run doctor
        </Button>
        <Button size="small" color="warning" disabled={busy} onClick={() => setConfirm(!(status.data?.cordon?.enabled))}>
          Soft Wall cordon {status.data?.cordon?.enabled ? "off" : "on"}
        </Button>
        <Button component={NextLink} href="/vault/setup" size="small" variant="outlined">
          Vault setup
        </Button>
      </Stack>
      <Dialog open={confirm !== null} onClose={() => setConfirm(null)}>
        <DialogTitle>Change cordon state?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Soft Wall confirm: set cordon enabled={String(confirm)}. No secret values are returned.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(null)}>Cancel</Button>
          <Button
            color="warning"
            variant="contained"
            disabled={busy}
            onClick={async () => {
              if (confirm === null) return;
              setBusy(true); setError(null);
              try {
                const response = await ceApi("/api/admin/proxy/cordon", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ enabled: confirm, force: true }),
                });
                const payload = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(parseApiErrorMessage(payload, "Cordon failed"));
                if (payload.blocked) {
                  setError(payload.message || "Soft Wall blocked");
                } else {
                  setMessage(`Cordon enabled=${String(confirm)}`);
                  setConfirm(null);
                  await status.mutate();
                }
              } catch (err) {
                setError(err instanceof Error ? err.message : "Cordon failed");
              } finally {
                setBusy(false);
              }
            }}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import LinkIcon from "@mui/icons-material/Link";
import LogoutIcon from "@mui/icons-material/Logout";
import RefreshIcon from "@mui/icons-material/Refresh";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";

type Status = {
  connected: boolean;
  account_email?: string | null;
  scopes: string[];
  missing_setup: string[];
  setup_error?: string | null;
};

const fetcher = async (url: string): Promise<Status> => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

export default function GoogleWorkspaceSettingsPage() {
  const { data, error, mutate, isLoading } = useSWR("/api/integrations/google-workspace/status", fetcher);
  const [message, setMessage] = React.useState<string | null>(null);

  async function startOAuth() {
    const response = await fetch("/api/integrations/google-workspace/oauth/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const payload = await response.json();
    if (!response.ok) {
      setMessage(payload.detail || "Google Workspace setup is incomplete.");
      return;
    }
    window.open(payload.auth_url, "_blank", "noopener,noreferrer");
  }

  async function logout() {
    await fetch("/api/integrations/google-workspace", { method: "DELETE" });
    setMessage("Google Workspace token metadata removed.");
    void mutate();
  }

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader title="Google Workspace" description="Connect Gmail, Calendar, Drive, Docs, and Sheets as one tier-1 operating surface." />
      {message ? <Alert severity={message.includes("incomplete") ? "warning" : "info"} onClose={() => setMessage(null)}>{message}</Alert> : null}
      {error ? <Alert severity="error">Failed to load Google Workspace status.</Alert> : null}
      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Chip color={data?.connected ? "success" : "default"} label={data?.connected ? "Connected" : "Not connected"} />
          {data?.account_email ? <Chip variant="outlined" label={data.account_email} /> : null}
          {data?.missing_setup?.map((item) => <Chip key={item} variant="outlined" color="warning" label={item} />)}
        </Stack>
        {data?.setup_error ? <Alert severity="warning">{data.setup_error}</Alert> : null}
        <Typography variant="body2" color="text.secondary">
          Token files are stored outside the repository. Enable Gmail, Calendar, Drive, and Sheets APIs in Google Cloud before connecting.
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button variant="contained" startIcon={<LinkIcon />} onClick={startOAuth} disabled={isLoading}>
            Connect
          </Button>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => void mutate()}>
            Refresh
          </Button>
          <Button variant="outlined" color="error" startIcon={<LogoutIcon />} onClick={logout}>
            Disconnect
          </Button>
        </Stack>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>Granted scopes</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          {(data?.scopes || []).map((scope) => <Chip key={scope} size="small" label={scope.replace("https://www.googleapis.com/auth/", "")} />)}
        </Stack>
      </Paper>
    </Box>
  );
}

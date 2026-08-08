"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { bindInterfaces, dispatchInterface, fetchInterfaces } from "@/lib/platform-admin-api";

export default function InterfacesPage() {
  const [agentId, setAgentId] = React.useState("default");
  const [kinds, setKinds] = React.useState("web_ui,api");
  const [message, setMessage] = React.useState("hello");
  const [kind, setKind] = React.useState("web_ui");
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<unknown>(null);
  const [busy, setBusy] = React.useState(false);
  const bound = useSWR(["interfaces", agentId], () => fetchInterfaces(agentId));

  return (
    <Box>
      <PageHeader title="Interfaces" description="Bind and dispatch agent interfaces." breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Interfaces" }]} />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Stack spacing={1.5}>
          <TextField size="small" label="Agent id" value={agentId} onChange={(e) => setAgentId(e.target.value)} />
          <TextField size="small" label="Kinds (comma)" value={kinds} onChange={(e) => setKinds(e.target.value)} />
          <Button variant="contained" disabled={busy} onClick={async () => {
            setBusy(true); setError(null);
            try { await bindInterfaces(agentId, kinds.split(",").map((k) => k.trim()).filter(Boolean)); await bound.mutate(); }
            catch (err) { setError(err instanceof Error ? err.message : "Bind failed"); }
            finally { setBusy(false); }
          }}>Bind</Button>
        </Stack>
      </Paper>
      <Typography variant="subtitle2">Bound</Typography>
      <StructuredDataView value={bound.data || {}} />
      <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
        <Stack spacing={1.5}>
          <TextField size="small" label="Dispatch kind" value={kind} onChange={(e) => setKind(e.target.value)} />
          <TextField size="small" label="Message" value={message} onChange={(e) => setMessage(e.target.value)} />
          <Button disabled={busy} onClick={async () => {
            setBusy(true); setError(null);
            try { setResult(await dispatchInterface({ agent_id: agentId, kind, message })); }
            catch (err) { setError(err instanceof Error ? err.message : "Dispatch failed"); }
            finally { setBusy(false); }
          }}>Dispatch</Button>
        </Stack>
        {result ? <Box sx={{ mt: 1 }}><StructuredDataView value={result} /></Box> : null}
      </Paper>
    </Box>
  );
}

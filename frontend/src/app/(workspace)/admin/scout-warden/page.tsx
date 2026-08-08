"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { fetchScoutWardenStatus, requestScoutScan } from "@/lib/parity-api";

export default function ScoutWardenPage() {
  const { data, error } = useSWR("scout-warden-status", fetchScoutWardenStatus);
  const [target, setTarget] = React.useState("https://example.com");
  const [result, setResult] = React.useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);

  const onScan = async () => {
    setBusy(true);
    setActionError(null);
    try {
      setResult(await requestScoutScan(target.trim()));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Scout Warden"
        description="Optional scan bridge. Disabled by default for Community Edition."
      />
      {error ? <Alert severity="warning" sx={{ mb: 2 }}>Admin access required for status.</Alert> : null}
      {actionError ? <Alert severity="error" sx={{ mb: 2 }}>{actionError}</Alert> : null}
      <Typography variant="body2" sx={{ mb: 2 }}>
        Enabled: {data?.enabled ? "yes" : "no"} (set KEPRIX_SCOUT_WARDEN_ENABLED=1 and URL/token to activate)
      </Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField
          size="small"
          fullWidth
          label="Target URL"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
        />
        <Button variant="contained" disabled={busy || !target.trim()} onClick={() => void onScan()}>
          Request scan
        </Button>
      </Stack>
      {result ? (
        <Box sx={{ mt: 2 }}>
          <StructuredDataView value={result} />
        </Box>
      ) : null}
    </Box>
  );
}

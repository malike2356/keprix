"use client";

import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import RefreshIcon from "@mui/icons-material/Refresh";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import {
  fetchHarnessSessions,
  fetchHarnessSnapshot,
  openHarnessSession,
  type HarnessSnapshot,
} from "@/lib/browser-api";

export default function BrowserSessionPanel() {
  const { data: sessions, mutate } = useSWR("browser-harness-sessions", () => fetchHarnessSessions());
  const [snapshot, setSnapshot] = React.useState<HarnessSnapshot | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const onOpen = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await openHarnessSession({
        objective: "Inspect current page",
        url: "https://example.com",
      });
      setSnapshot(created.snapshot);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open harness session");
    } finally {
      setBusy(false);
    }
  };

  const onRefresh = async (sessionId: string) => {
    setBusy(true);
    setError(null);
    try {
      const snap = await fetchHarnessSnapshot(sessionId);
      setSnapshot(snap);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not refresh snapshot");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6">Browser harness sessions</Typography>
          <Button size="small" variant="contained" onClick={onOpen} disabled={busy}>
            Open session
          </Button>
        </Box>
        {error ? (
          <Typography color="error" variant="body2" sx={{ mb: 2 }}>
            {error}
          </Typography>
        ) : null}
        <List dense>
          {(sessions?.sessions ?? []).map((session) => (
            <ListItem
              key={session.session_id}
              secondaryAction={
                <Button size="small" startIcon={<RefreshIcon />} onClick={() => onRefresh(session.session_id)}>
                  Snapshot
                </Button>
              }
            >
              <ListItemText
                primary={session.objective}
                secondary={`${session.url} · trace ${session.trace_id.slice(0, 8)}`}
              />
            </ListItem>
          ))}
        </List>
        {snapshot ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Active snapshot
            </Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 1 }}>
              <Chip size="small" label={snapshot.url} icon={<OpenInNewIcon />} />
              <Chip size="small" label={`${snapshot.accessibility_tree.length} a11y nodes`} />
              <Chip size="small" label={`${snapshot.network_summary.length} network events`} />
            </Box>
            <Typography variant="caption" component="pre" sx={{ whiteSpace: "pre-wrap", bgcolor: "action.hover", p: 1, borderRadius: 1 }}>
              {snapshot.dom_snapshot.slice(0, 1200)}
            </Typography>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}

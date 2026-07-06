"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import BrowserSessionPanel from "@/components/browser/BrowserSessionPanel";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonTable } from "@/components/ui/loading";
import {
  fetchBrowserSessionSteps,
  fetchBrowserSessions,
  type BrowserSessionStep,
  type HarnessSession,
} from "@/lib/browser-api";

function modeColor(mode?: string): "default" | "info" {
  return mode === "live" ? "info" : "default";
}

function shortId(value: string): string {
  return value.length > 10 ? `${value.slice(0, 8)}...` : value;
}

export default function BrowserWorkspacePage() {
  const { data, error, isLoading, mutate } = useSWR("browser-sessions", () => fetchBrowserSessions());
  const [selected, setSelected] = React.useState<HarnessSession | null>(null);
  const [steps, setSteps] = React.useState<BrowserSessionStep[]>([]);
  const [stepsLoading, setStepsLoading] = React.useState(false);
  const [stepsError, setStepsError] = React.useState<string | null>(null);

  const sessions = data?.sessions ?? [];

  const openReplay = async (session: HarnessSession) => {
    setSelected(session);
    setStepsLoading(true);
    setStepsError(null);
    try {
      const payload = await fetchBrowserSessionSteps(session.session_id);
      setSteps(payload.steps || []);
    } catch (err) {
      setSteps([]);
      setStepsError(err instanceof Error ? err.message : "Could not load session steps");
    } finally {
      setStepsLoading(false);
    }
  };

  const closeReplay = () => {
    setSelected(null);
    setSteps([]);
    setStepsError(null);
  };

  return (
    <Box>
      <PageHeader
        title="Browser"
        description="Session history, step replay, and active harness controls. Profiles stay under settings."
        actions={
          <Button component={NextLink} href="/settings/browser" variant="outlined" size="small">
            Profile settings
          </Button>
        }
      />

      <Box sx={{ mb: 2 }}>
        <BrowserSessionPanel />
      </Box>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Session history
      </Typography>

      {error ? (
        <Typography color="error" variant="body2" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Failed to load browser sessions"}
        </Typography>
      ) : null}

      {isLoading ? (
        <SkeletonTable rows={4} columns={5} />
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No browser sessions yet"
          description="Open a harness session above or run a browser playbook to populate history."
        />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Objective</TableCell>
              <TableCell>Mode</TableCell>
              <TableCell>URL</TableCell>
              <TableCell>Steps</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sessions.map((session) => (
              <TableRow key={session.session_id} hover>
                <TableCell>{session.objective}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={session.mode === "live" ? "live" : "dry run"}
                    color={modeColor(session.mode)}
                  />
                </TableCell>
                <TableCell>
                  <Link href={session.url} target="_blank" rel="noreferrer">
                    {session.url}
                  </Link>
                </TableCell>
                <TableCell>{session.step_count ?? 0}</TableCell>
                <TableCell>{session.created_at ? new Date(session.created_at).toLocaleString() : shortId(session.session_id)}</TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => openReplay(session)}>
                    Replay steps
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Drawer anchor="right" open={Boolean(selected)} onClose={closeReplay} PaperProps={{ sx: { width: { xs: "100%", sm: 420 }, p: 2 } }}>
        {selected ? (
          <Box>
            <Typography variant="h6" gutterBottom>
              Step replay
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {selected.objective} · {selected.mode === "live" ? "live" : "dry run"}
            </Typography>
            {stepsError ? (
              <Typography color="error" variant="body2" sx={{ mb: 2 }}>
                {stepsError}
              </Typography>
            ) : null}
            {stepsLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading steps...
              </Typography>
            ) : steps.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No recorded steps for this session.
              </Typography>
            ) : (
              <Box sx={{ display: "grid", gap: 1.5 }}>
                {steps.map((step) => (
                  <Box
                    key={step.id}
                    sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.25 }}
                  >
                    <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 0.5 }}>
                      <Chip size="small" label={step.action} />
                      <Chip size="small" variant="outlined" label={step.status} />
                      <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
                        {new Date(step.created_at).toLocaleTimeString()}
                      </Typography>
                    </Box>
                    {step.selector ? (
                      <Typography variant="caption" color="text.secondary">
                        selector: {step.selector}
                      </Typography>
                    ) : null}
                  </Box>
                ))}
              </Box>
            )}
            <Button sx={{ mt: 2 }} onClick={() => void mutate()}>
              Refresh history
            </Button>
          </Box>
        ) : null}
      </Drawer>
    </Box>
  );
}

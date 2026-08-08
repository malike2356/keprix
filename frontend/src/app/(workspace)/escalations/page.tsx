"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  assignEscalation,
  completeEscalation,
  fetchEscalationQueue,
  type EscalationItem,
} from "@/lib/escalations-api";

export default function EscalationsPage() {
  const workspaceId = "default";
  const [status, setStatus] = React.useState<string | null>("pending");
  const [assignee, setAssignee] = React.useState("operator");
  const [responses, setResponses] = React.useState<Record<string, string>>({});
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);

  const queue = useSWR(["escalations", workspaceId, status], () =>
    fetchEscalationQueue(workspaceId, status),
  );

  const onAssign = async (item: EscalationItem) => {
    setBusyId(item.id);
    setActionError(null);
    try {
      await assignEscalation(item.id, assignee.trim() || "operator");
      await queue.mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Assign failed");
    } finally {
      setBusyId(null);
    }
  };

  const onComplete = async (item: EscalationItem) => {
    const reply = (responses[item.id] || "").trim();
    if (!reply) {
      setActionError("Enter a VA response before completing");
      return;
    }
    setBusyId(item.id);
    setActionError(null);
    try {
      await completeEscalation(item.id, reply, assignee.trim() || undefined);
      await queue.mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Complete failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Escalations"
        description="Human VA queue for low-confidence or out-of-scope agent turns. Use this when running Keprix as a standalone OS."
        actions={
          <Stack direction="row" spacing={1} alignItems="center">
            <TextField
              size="small"
              label="Assignee"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              sx={{ width: 160 }}
            />
            <ButtonGroup size="small" variant="outlined">
              {["pending", "in_progress", "completed", "timed_out", null].map((value) => (
                <Button
                  key={String(value)}
                  variant={status === value ? "contained" : "outlined"}
                  onClick={() => setStatus(value)}
                >
                  {value ?? "all"}
                </Button>
              ))}
            </ButtonGroup>
          </Stack>
        }
      />

      {queue.error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {queue.error.message}
        </Alert>
      ) : null}
      {actionError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {actionError}
        </Alert>
      ) : null}

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {queue.data ? `${queue.data.count} escalation(s)` : "Loading…"}
      </Typography>

      <Stack spacing={1.5}>
        {(queue.data?.items ?? []).map((item) => (
          <Card key={item.id} variant="outlined">
            <CardContent>
              <Stack spacing={1}>
                <Stack direction="row" justifyContent="space-between" gap={1} flexWrap="wrap">
                  <Typography variant="subtitle1" fontWeight={600}>
                    {item.escalation_type || "escalation"} · {item.status}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {item.worker_id || "unassigned"} · {item.created_at || ""}
                  </Typography>
                </Stack>
                <Typography variant="body2">{item.original_input || "(no input)"}</Typography>
                {item.holding_message ? (
                  <Typography variant="caption" color="text.secondary">
                    Holding: {item.holding_message}
                  </Typography>
                ) : null}
                <TextField
                  size="small"
                  fullWidth
                  multiline
                  minRows={2}
                  label="VA response"
                  value={responses[item.id] || ""}
                  onChange={(e) => setResponses((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  disabled={item.status === "completed"}
                />
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={busyId === item.id || item.status === "completed"}
                    onClick={() => void onAssign(item)}
                  >
                    Assign
                  </Button>
                  <Button
                    size="small"
                    variant="contained"
                    disabled={busyId === item.id || item.status === "completed"}
                    onClick={() => void onComplete(item)}
                  >
                    Complete
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ))}
        {!queue.isLoading && (queue.data?.items?.length ?? 0) === 0 ? (
          <Alert severity="info">No escalations in this filter. New ones appear when agents escalate.</Alert>
        ) : null}
      </Stack>
    </Box>
  );
}

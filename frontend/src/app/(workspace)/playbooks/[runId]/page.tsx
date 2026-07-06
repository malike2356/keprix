"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/loading";
import {
  approvalResumePatch,
  cancelPlaybookRun,
  fetchPlaybookRun,
  fetchPlaybookRunEvents,
  formatPlaybookEventLabel,
  pausePlaybookRun,
  resumePlaybookRun,
  type PlaybookRun,
  type PlaybookRunStatus,
} from "@/lib/playbook-api";
import { useCESession } from "@/lib/ce-auth";

function statusColor(
  status: PlaybookRunStatus,
): "default" | "success" | "warning" | "error" | "info" {
  if (status === "completed") return "success";
  if (status === "failed" || status === "cancelled") return "error";
  if (status === "running" || status === "pending") return "info";
  if (status === "interrupted" || status === "waiting_for_approval") return "warning";
  return "default";
}

function shouldPoll(status: PlaybookRunStatus): boolean {
  return status === "running" || status === "paused" || status === "pending";
}

function needsApproval(status: PlaybookRunStatus): boolean {
  return status === "interrupted" || status === "waiting_for_approval";
}

export default function PlaybookRunDetailPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const router = useRouter();
  const { user } = useCESession();
  const [stateOpen, setStateOpen] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [actionMessage, setActionMessage] = React.useState<string | null>(null);
  const [acting, setActing] = React.useState(false);

  const {
    data: run,
    error: runError,
    isLoading,
    mutate: mutateRun,
  } = useSWR(runId ? `playbook-run-${runId}` : null, () => fetchPlaybookRun(runId), {
    refreshInterval: (latest) => (latest && shouldPoll(latest.status) ? 2000 : 0),
  });

  const { data: eventsData, mutate: mutateEvents } = useSWR(
    runId ? `playbook-run-events-${runId}` : null,
    () => fetchPlaybookRunEvents(runId),
    {
      refreshInterval: run && shouldPoll(run.status) ? 2000 : 0,
    },
  );

  const events = eventsData?.events ?? [];

  const runAction = async (action: () => Promise<PlaybookRun>, success: string) => {
    setActing(true);
    setActionError(null);
    setActionMessage(null);
    try {
      await action();
      setActionMessage(success);
      await mutateRun();
      await mutateEvents();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActing(false);
    }
  };

  const handleApprove = () => {
    if (!run) return;
    void runAction(
      () => resumePlaybookRun(runId, approvalResumePatch(run), user?.username || "web"),
      "Playbook resumed after approval",
    );
  };

  const handleReject = () => {
    void runAction(() => cancelPlaybookRun(runId), "Playbook run cancelled");
  };

  if (isLoading) {
    return (
      <Box>
        <PageHeader title="Playbook run" description="Loading run details..." />
        <SkeletonBlock height={240} />
      </Box>
    );
  }

  if (runError || !run) {
    return (
      <Box>
        <PageHeader title="Playbook run" description="Run not found" />
        <Alert severity="error">
          {runError instanceof Error ? runError.message : "Playbook run not found"}
        </Alert>
        <Button sx={{ mt: 2 }} onClick={() => router.push("/playbooks")}>
          Back to playbooks
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title={`Playbook: ${run.graph_id}`}
        description={`Run ${run.run_id}`}
        actions={
          <Button variant="outlined" onClick={() => router.push("/playbooks")}>
            All playbooks
          </Button>
        }
      />

      {actionMessage ? <Alert severity="success" sx={{ mb: 2 }}>{actionMessage}</Alert> : null}
      {actionError ? <Alert severity="error" sx={{ mb: 2 }}>{actionError}</Alert> : null}

      {needsApproval(run.status) ? (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={
            <Box sx={{ display: "flex", gap: 1 }}>
              <Button color="inherit" size="small" disabled={acting} onClick={handleApprove}>
                Approve
              </Button>
              <Button color="inherit" size="small" disabled={acting} onClick={handleReject}>
                Reject
              </Button>
            </Box>
          }
        >
          {run.interrupt_reason ||
            String(run.approval_request?.summary || "Human approval required to continue")}
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center", mb: 2 }}>
            <Chip size="small" color={statusColor(run.status)} label={run.status} />
            {run.current_node ? <Chip size="small" variant="outlined" label={`Node: ${run.current_node}`} /> : null}
            <Chip size="small" variant="outlined" label={run.workspace_id} />
          </Box>
          {run.error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {run.error}
            </Alert>
          ) : null}
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Button
              size="small"
              variant="outlined"
              disabled={acting || run.status !== "running"}
              onClick={() => void runAction(() => pausePlaybookRun(runId), "Playbook paused")}
            >
              Pause
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={acting || !["paused", "failed"].includes(run.status)}
              onClick={() =>
                void runAction(
                  () => resumePlaybookRun(runId, {}, user?.username || "web"),
                  "Playbook resumed",
                )
              }
            >
              Resume
            </Button>
            <Button
              size="small"
              color="error"
              variant="outlined"
              disabled={acting || ["completed", "cancelled"].includes(run.status)}
              onClick={() => void runAction(() => cancelPlaybookRun(runId), "Playbook cancelled")}
            >
              Cancel
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Event timeline
      </Typography>
      <Card variant="outlined" sx={{ mb: 2 }}>
        <List dense>
          {events.length === 0 ? (
            <ListItem>
              <ListItemText primary="No events yet" />
            </ListItem>
          ) : (
            events.map((event) => (
              <ListItem key={event.event_id} alignItems="flex-start">
                <ListItemText
                  primary={formatPlaybookEventLabel(event)}
                  secondary={new Date(event.timestamp).toLocaleString()}
                />
              </ListItem>
            ))
          )}
        </List>
      </Card>

      <Button
        size="small"
        startIcon={stateOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        onClick={() => setStateOpen((open) => !open)}
        sx={{ mb: 1 }}
      >
        State inspector
      </Button>
      <Collapse in={stateOpen}>
        <Card variant="outlined">
          <CardContent>
            <Typography
              component="pre"
              variant="body2"
              sx={{ m: 0, whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 12 }}
            >
              {JSON.stringify(run.state, null, 2)}
            </Typography>
            {run.artifacts && run.artifacts.length > 0 ? (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Artifacts
                </Typography>
                <Typography
                  component="pre"
                  variant="body2"
                  sx={{ m: 0, whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 12 }}
                >
                  {JSON.stringify(run.artifacts, null, 2)}
                </Typography>
              </>
            ) : null}
          </CardContent>
        </Card>
      </Collapse>
    </Box>
  );
}

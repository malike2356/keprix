"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid2";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import AgentTraceViewer from "@/components/traces/AgentTraceViewer";
import RealtimeAgentPanel from "@/components/realtime/RealtimeAgentPanel";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchAgentAppRuntimeRuns,
  fetchAgents,
  fetchRunTrace,
  handoffRun,
  startAgentRun,
  type TraceView,
} from "@/lib/agents-runtime-api";

export default function AgentRuntimePage() {
  const searchParams = useSearchParams();
  const source = searchParams.get("source");
  const appFilter = searchParams.get("app");
  const traceParam = searchParams.get("trace_id");
  const isAgentAppView = source === "agent_app" && Boolean(appFilter);

  const [agent, setAgent] = React.useState("support_agent");
  const [input, setInput] = React.useState("Customer needs help with invoice #42");
  const [runId, setRunId] = React.useState<string | null>(traceParam);
  const [trace, setTrace] = React.useState<TraceView | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const { data: agentsData } = useSWR("agents-runtime-agents", fetchAgents);
  const { data: agentAppRuns } = useSWR(
    isAgentAppView && appFilter ? ["agent-app-runtime-runs", appFilter] : null,
    () => fetchAgentAppRuntimeRuns(appFilter as string),
  );
  const agents = agentsData?.agents ?? [];

  const refreshTrace = React.useCallback(async (id: string) => {
    const view = await fetchRunTrace(id);
    setTrace(view);
  }, []);

  React.useEffect(() => {
    if (traceParam) {
      setRunId(traceParam);
      refreshTrace(traceParam).catch(() => undefined);
    }
  }, [traceParam, refreshTrace]);

  const runAction = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Agent Runtime"
        description={
          isAgentAppView
            ? `Persisted traces for agent app ${appFilter}.`
            : "Handoffs, guardrails, traces, and realtime voice lane (provider-agnostic)."
        }
      />
      {isAgentAppView ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          Showing agent app runs for <strong>{appFilter}</strong>.{" "}
          <Link href={`/agent-apps/${encodeURIComponent(appFilter || "")}`}>Back to app</Link>
        </Alert>
      ) : null}
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {isAgentAppView ? "Agent app runs" : "Run agent"}
              </Typography>
              {isAgentAppView ? (
                <Box sx={{ display: "grid", gap: 1 }}>
                  {(agentAppRuns?.runs ?? []).map((run: { trace_id: string; status: string; input_preview?: string }) => (
                    <Button
                      key={run.trace_id}
                      variant={runId === run.trace_id ? "contained" : "outlined"}
                      onClick={() =>
                        runAction(async () => {
                          setRunId(run.trace_id);
                          await refreshTrace(run.trace_id);
                          setMessage(`Loaded trace ${run.trace_id}`);
                        })
                      }
                      sx={{ justifyContent: "flex-start", textAlign: "left" }}
                    >
                      <Box>
                        <Typography variant="body2">{run.status}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {run.input_preview || run.trace_id}
                        </Typography>
                      </Box>
                    </Button>
                  ))}
                  {!agentAppRuns?.runs?.length ? (
                    <Typography variant="body2" color="text.secondary">
                      No persisted runs for this app yet.
                    </Typography>
                  ) : null}
                </Box>
              ) : (
                <>
              <TextField
                select
                fullWidth
                label="Agent"
                value={agent}
                onChange={(e) => setAgent(e.target.value)}
                sx={{ mb: 2 }}
              >
                {agents.map((item: { name: string }) => (
                  <MenuItem key={item.name} value={item.name}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                fullWidth
                multiline
                minRows={3}
                label="Input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                sx={{ mb: 2 }}
              />
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Button
                  variant="contained"
                  disabled={busy}
                  onClick={() =>
                    runAction(async () => {
                      const result = await startAgentRun({ agent, input });
                      setRunId(result.run_id);
                      await refreshTrace(result.run_id);
                      setMessage(`Run started as ${result.agent ?? agent}`);
                    })
                  }
                >
                  Start run
                </Button>
                <Button
                  variant="outlined"
                  disabled={busy || !runId}
                  onClick={() =>
                    runAction(async () => {
                      if (!runId) return;
                      await handoffRun(runId, {
                        target: "billing_agent",
                        reason: "Billing question detected",
                      });
                      await refreshTrace(runId);
                      setMessage("Handed off to billing_agent");
                    })
                  }
                >
                  Handoff to billing
                </Button>
              </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Trace
              </Typography>
              <AgentTraceViewer trace={trace} />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <RealtimeAgentPanel />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

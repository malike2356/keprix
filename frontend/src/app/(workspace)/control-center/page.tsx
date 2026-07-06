"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import ActivityFeed from "@/components/control-center/ActivityFeed";
import AgentServerList from "@/components/control-center/AgentServerList";
import AutomationRules from "@/components/control-center/AutomationRules";
import RunQueue from "@/components/control-center/RunQueue";
import PageHeader from "@/components/ui/PageHeader";
import {
  createScheduledAutomation,
  createWebhookAutomation,
  fetchControlDashboard,
  registerAgentServer,
  triggerAutomation,
} from "@/lib/control-center-api";

export default function ControlCenterPage() {
  const { data, mutate } = useSWR("control-center-dashboard", fetchControlDashboard);
  const [serverName, setServerName] = React.useState("local-agent");
  const [workspaceRoot, setWorkspaceRoot] = React.useState("");
  const [playbookId, setPlaybookId] = React.useState("starter-team");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function handleRegisterServer() {
    setError(null);
    setMessage(null);
    try {
      await registerAgentServer({
        name: serverName,
        url: "http://127.0.0.1:8000",
        workspace_root: workspaceRoot,
      });
      setMessage("Agent server registered.");
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  async function handleSchedule() {
    setError(null);
    setMessage(null);
    try {
      await createScheduledAutomation({
        name: "Daily playbook",
        playbook_id: playbookId,
        schedule_cron: "0 9 * * *",
      });
      setMessage("Scheduled automation created.");
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Schedule failed");
    }
  }

  async function handleWebhook() {
    setError(null);
    setMessage(null);
    try {
      const result = await createWebhookAutomation({
        name: "Webhook playbook",
        playbook_id: playbookId,
      });
      setMessage(`Webhook ready at ${result.webhook_path}`);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Webhook setup failed");
    }
  }

  async function handleTrigger(automationId: string) {
    setError(null);
    try {
      await triggerAutomation(automationId);
      setMessage("Automation triggered.");
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trigger failed");
    }
  }

  return (
    <Box>
      <PageHeader
        title="Control Center"
        description="Self-hosted control plane for agent servers, long-running sessions, automations, and team-visible activity."
      />
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, mb: 2 }}>
        <AgentServerList servers={data?.servers ?? []} />
        <AutomationRules automations={data?.automations ?? []} onTrigger={handleTrigger} />
      </Box>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, mb: 2 }}>
        <RunQueue queued={data?.queued_runs ?? []} failed={data?.failed_runs ?? []} />
        <ActivityFeed
          activity={data?.activity ?? []}
          approvals={data?.approvals ?? []}
          artifacts={data?.recent_artifacts ?? []}
        />
      </Box>
      <Box sx={{ display: "grid", gap: 2, maxWidth: 480 }}>
        <TextField size="small" label="Server name" value={serverName} onChange={(e) => setServerName(e.target.value)} />
        <TextField
          size="small"
          label="Workspace root (allowlisted path)"
          value={workspaceRoot}
          onChange={(e) => setWorkspaceRoot(e.target.value)}
        />
        <TextField size="small" label="Playbook id" value={playbookId} onChange={(e) => setPlaybookId(e.target.value)} />
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Button variant="contained" onClick={handleRegisterServer} disabled={!workspaceRoot}>
            Register local server
          </Button>
          <Button variant="outlined" onClick={handleSchedule}>
            Add schedule
          </Button>
          <Button variant="outlined" onClick={handleWebhook}>
            Add webhook
          </Button>
        </Box>
        {message ? <Typography variant="body2">{message}</Typography> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}
      </Box>
    </Box>
  );
}

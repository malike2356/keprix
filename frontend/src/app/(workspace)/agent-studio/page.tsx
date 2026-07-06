"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import AgentCanvas from "@/components/agent-studio/AgentCanvas";
import AgentRolePanel from "@/components/agent-studio/AgentRolePanel";
import RunStreamPanel from "@/components/agent-studio/RunStreamPanel";
import ToolWorkbenchPanel from "@/components/agent-studio/ToolWorkbenchPanel";
import PageHeader from "@/components/ui/PageHeader";
import { fetchAgentRoles, savePlaybook, type StudioConnection } from "@/lib/multiagent-api";

export default function AgentStudioPage() {
  const { data } = useSWR("agent-studio-roles", fetchAgentRoles);
  const roles = data?.roles ?? [];
  const [selectedRole, setSelectedRole] = React.useState<string | null>(null);
  const [policy, setPolicy] = React.useState("supervisor_moderated");
  const [supervisor, setSupervisor] = React.useState("");
  const [playbookName, setPlaybookName] = React.useState("starter-team");
  const [connections, setConnections] = React.useState<StudioConnection[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!roles.length) return;
    const names = roles.map((role) => role.name);
    if (!selectedRole || !names.includes(selectedRole)) {
      setSelectedRole(names[0]);
    }
    if (!supervisor || !names.includes(supervisor)) {
      setSupervisor(names[0]);
    }
    if (connections.length === 0 && names.length >= 2) {
      setConnections([{ from: names[0], to: names[1] }]);
    }
  }, [roles, selectedRole, supervisor, connections.length]);

  function handleConnect() {
    if (!selectedRole || !supervisor || selectedRole === supervisor) {
      return;
    }
    setConnections((current) => [...current, { from: supervisor, to: selectedRole }]);
  }

  async function handleSave() {
    setMessage(null);
    setError(null);
    const roleMap = Object.fromEntries(
      roles.map((role) => [
        role.name,
        {
          goal: role.goal,
          backstory: role.backstory ?? "",
          tools: role.tools ?? [],
          connects_to: connections.filter((item) => item.from === role.name).map((item) => item.to),
        },
      ]),
    );
    try {
      const result = await savePlaybook({
        name: playbookName,
        workspace_id: "local",
        roles: roleMap,
        connections,
        group_chat: {
          policy,
          supervisor,
          participants: roles.map((role) => role.name),
        },
        mcp_servers: [{ name: "filesystem", trusted: true, bound_tools: ["read_file"] }],
      });
      setMessage(`Saved playbook to ${result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  return (
    <Box>
      <PageHeader
        title="Agent Studio"
        description="Build multi-agent teams, bind MCP tools, define group chat policy, and dry-run playbooks."
        actions={
          <Button component={Link} href="/agent-apps" size="small" variant="outlined">
            Agent apps
          </Button>
        }
      />
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, mb: 2 }}>
        <AgentRolePanel
          roles={roles}
          selectedRole={selectedRole}
          onSelectRole={setSelectedRole}
          policy={policy}
          onPolicyChange={setPolicy}
          supervisor={supervisor}
          onSupervisorChange={setSupervisor}
          playbookName={playbookName}
          onPlaybookNameChange={setPlaybookName}
          onConnect={handleConnect}
        />
        <AgentCanvas
          roles={roles.map((role) => role.name)}
          connections={connections}
          selectedRole={selectedRole}
          onSelectRole={setSelectedRole}
        />
      </Box>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, mb: 2 }}>
        <ToolWorkbenchPanel agentId={selectedRole} />
        <RunStreamPanel playbookName={playbookName} />
      </Box>
      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
        <Button variant="contained" onClick={handleSave}>
          Save playbook YAML
        </Button>
        {message ? <Typography variant="body2">{message}</Typography> : null}
      </Box>
      {error ? (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      ) : null}
    </Box>
  );
}

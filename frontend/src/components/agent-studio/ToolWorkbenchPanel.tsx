"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import type { McpTool } from "@/lib/multiagent-api";
import { bindMcpTools, fetchMcpTools, registerMcpServer } from "@/lib/multiagent-api";

type ToolWorkbenchPanelProps = {
  agentId: string | null;
};

function riskColor(risk: string): "success" | "warning" | "error" | "default" {
  if (risk === "low") return "success";
  if (risk === "medium") return "warning";
  if (risk === "high" || risk === "critical") return "error";
  return "default";
}

export default function ToolWorkbenchPanel({ agentId }: ToolWorkbenchPanelProps) {
  const { data } = useSWR("mcp-tools", () => fetchMcpTools());
  const tools = data?.tools ?? [];
  const [server, setServer] = React.useState("");
  const [selected, setSelected] = React.useState<string[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const servers = React.useMemo(
    () => Array.from(new Set(tools.map((tool: McpTool) => tool.server))),
    [tools],
  );

  React.useEffect(() => {
    if (!servers.length) {
      setServer("");
      return;
    }
    if (!servers.includes(server)) {
      setServer(servers[0]);
    }
  }, [servers, server]);

  async function handleBind() {
    if (!agentId) {
      setError("Select an agent role first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      await registerMcpServer(server, true);
      const result = await bindMcpTools(agentId, server, selected);
      setMessage(`Bound ${result.bound_tools.join(", ")} to ${agentId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bind failed");
    }
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          MCP workbench
        </Typography>
        <TextField
          select
          fullWidth
          size="small"
          label="Server"
          value={servers.includes(server) ? server : ""}
          onChange={(event) => setServer(event.target.value)}
          sx={{ mb: 2 }}
          SelectProps={{ displayEmpty: true }}
          disabled={!servers.length}
        >
          <MenuItem value="">
            <em>{servers.length ? "Select server" : "No MCP servers available"}</em>
          </MenuItem>
          {servers.map((item) => (
            <MenuItem key={item} value={item}>
              {item}
            </MenuItem>
          ))}
        </TextField>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
          {tools
            .filter((tool) => tool.server === server)
            .map((tool) => {
              const active = selected.includes(tool.name);
              return (
                <Chip
                  key={`${tool.server}.${tool.name}`}
                  label={`${tool.name} (${tool.risk})`}
                  color={riskColor(tool.risk)}
                  variant={active ? "filled" : "outlined"}
                  onClick={() =>
                    setSelected((current) =>
                      active ? current.filter((name) => name !== tool.name) : [...current, tool.name],
                    )
                  }
                  clickable
                />
              );
            })}
        </Box>
        <Button size="small" variant="contained" onClick={handleBind} disabled={!agentId || selected.length === 0}>
          Bind selected tools
        </Button>
        {message ? (
          <Alert severity="success" sx={{ mt: 2 }}>
            {message}
          </Alert>
        ) : null}
        {error ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

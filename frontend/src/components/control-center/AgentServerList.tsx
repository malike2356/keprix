"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { AgentServer } from "@/lib/control-center-api";

type AgentServerListProps = {
  servers: AgentServer[];
};

function healthColor(status: string): "success" | "warning" | "error" | "default" {
  if (status === "healthy" || status === "local") return "success";
  if (status === "degraded" || status === "unknown") return "warning";
  return "error";
}

export default function AgentServerList({ servers }: AgentServerListProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Agent servers
        </Typography>
        {servers.length === 0 ? (
          <Typography variant="body2">No agent servers registered.</Typography>
        ) : (
          servers.map((server) => (
            <Box key={server.id} sx={{ mb: 2, pb: 2, borderBottom: "1px solid", borderColor: "divider" }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 0.5 }}>
                <Typography variant="body1">{server.name}</Typography>
                <Chip size="small" color={healthColor(server.health_status)} label={server.health_status} />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {server.url}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Workspace: {server.workspace_root}
              </Typography>
            </Box>
          ))
        )}
      </CardContent>
    </Card>
  );
}

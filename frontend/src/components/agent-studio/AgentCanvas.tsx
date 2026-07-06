"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { StudioConnection } from "@/lib/multiagent-api";

type AgentCanvasProps = {
  roles: string[];
  connections: StudioConnection[];
  selectedRole: string | null;
  onSelectRole: (role: string) => void;
};

export default function AgentCanvas({ roles, connections, selectedRole, onSelectRole }: AgentCanvasProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Agent graph
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
          {roles.map((role) => (
            <Chip
              key={role}
              label={role}
              color={selectedRole === role ? "primary" : "default"}
              onClick={() => onSelectRole(role)}
              clickable
            />
          ))}
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Connections
        </Typography>
        {connections.length === 0 ? (
          <Typography variant="body2">No connections yet.</Typography>
        ) : (
          connections.map((connection, index) => (
            <Typography key={`${connection.from}-${connection.to}-${index}`} variant="body2">
              {connection.from} {"->"} {connection.to}
            </Typography>
          ))
        )}
      </CardContent>
    </Card>
  );
}

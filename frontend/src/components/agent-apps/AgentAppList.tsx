"use client";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { fetchAgentApps } from "@/lib/agent-apps-api";

export default function AgentAppList() {
  const router = useRouter();
  const { data, isLoading } = useSWR("agent-apps", fetchAgentApps);

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Installed agent apps
        </Typography>
        {isLoading ? <Typography variant="body2">Loading...</Typography> : null}
        <List dense disablePadding>
          {(data?.apps ?? []).map((app) => (
            <ListItemButton key={app.name} onClick={() => router.push(`/agent-apps/${app.name}`)}>
              <ListItemText
                primary={app.display_name || app.name}
                secondary={`v${app.version}${app.description ? ` · ${app.description}` : ""}`}
              />
              <Chip size="small" label="Open" />
            </ListItemButton>
          ))}
        </List>
      </CardContent>
    </Card>
  );
}

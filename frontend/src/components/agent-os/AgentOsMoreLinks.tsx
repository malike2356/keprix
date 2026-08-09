"use client";

import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { AGENT_OS_MORE_LINKS } from "@/components/agent-os/AgentOsSubnav";

export default function AgentOsMoreLinks() {
  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        More Agent OS
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {AGENT_OS_MORE_LINKS.map((item) => (
          <Button key={item.href} component="a" href={item.href} size="small" variant="text">
            {item.label}
          </Button>
        ))}
      </Stack>
    </Paper>
  );
}

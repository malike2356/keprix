"use client";

import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

const CHANNELS = [
  {
    href: "/outreach/approvals",
    title: "Email Soft Wall",
    description: "Approve sequence drafts before send. Required for every cold touch. No mass-send without approval.",
  },
  {
    href: "/review-gateway",
    title: "Review Gateway",
    description: "Operator review surface for outbound and risky actions.",
  },
  {
    href: "/outreach/companies-house",
    title: "Companies House",
    description: "Search UK company registry and import leads into outreach.",
  },
  {
    href: "/email",
    title: "Mailbox",
    description: "Read replies and triage interest back into the pipeline.",
  },
  {
    href: "/companies-house",
    title: "Companies House (standalone)",
    description: "Full registry browser outside the outreach module.",
  },
] as const;

export default function OutreachChannelsPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Content and engagement channels that feed sales engagement. Email sequences live under Sequences and
        Approvals; Soft Wall gates outbound sends. Open a card to jump to that channel.
      </Typography>
      <Grid container spacing={1.5}>
        {CHANNELS.map((item) => (
          <Grid key={item.href} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              {/* Plain <a>: MUI CardActionArea + next/link often drops navigation in the workspace shell. */}
              <CardActionArea
                component="a"
                href={item.href}
                sx={{ height: "100%", alignItems: "stretch" }}
              >
                <CardContent>
                  <Typography variant="subtitle1">{item.title}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {item.description}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}

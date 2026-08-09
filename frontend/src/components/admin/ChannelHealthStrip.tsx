"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonBlock } from "@/components/ui/loading";
import type { ChannelStatus } from "@/lib/admin-dashboard-api";

type ChannelHealthStripProps = {
  channels?: ChannelStatus[];
  loading?: boolean;
};

function dotColor(status: ChannelStatus["status"]): string {
  if (status === "connected") return "success.main";
  if (status === "degraded") return "warning.main";
  return "error.main";
}

export default function ChannelHealthStrip({ channels = [], loading }: ChannelHealthStripProps) {
  if (loading) {
    return (
      <DashboardCard title="Channel health">
        <SkeletonBlock height={72} />
      </DashboardCard>
    );
  }

  return (
    <DashboardCard title="Channel health" subtitle="Connected surfaces and last activity">
      {channels.length === 0 ? (
        <Box sx={{ py: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            No channels connected yet.
          </Typography>
          <Button component="a" href="/admin/channels" size="small" variant="outlined">
            Configure channels
          </Button>
        </Box>
      ) : (
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        {channels.map((channel) => (
          <Card key={channel.id} variant="outlined" sx={{ flex: 1, bgcolor: "background.default" }}>
            <CardContent sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, py: 2, "&:last-child": { pb: 2 } }}>
              <Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: dotColor(channel.status) }} />
                  <Typography variant="subtitle2">{channel.name}</Typography>
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {channel.last_message_at
                    ? `Last message ${new Date(channel.last_message_at).toLocaleString()}`
                    : "No recent messages"}
                </Typography>
              </Box>
              <Button component="a" href={channel.configure_href} size="small" variant="outlined">
                Configure
              </Button>
            </CardContent>
          </Card>
        ))}
      </Stack>
      )}
    </DashboardCard>
  );
}

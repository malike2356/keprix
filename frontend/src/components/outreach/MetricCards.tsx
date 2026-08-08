"use client";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import type { OutreachOverview } from "@/components/outreach/types";

type MetricCardsProps = {
  overview: OutreachOverview | null;
};

const METRICS: Array<{
  label: string;
  value: (overview: OutreachOverview) => number;
}> = [
  { label: "Total leads", value: (o) => o.summary?.total ?? 0 },
  { label: "Active enrollments", value: (o) => o.activeEnrollments ?? 0 },
  { label: "Pending Soft Wall", value: (o) => o.pendingApprovals ?? 0 },
  { label: "Booked", value: (o) => o.summary?.booked ?? 0 },
  { label: "Open reply reviews", value: (o) => o.openReplyReviews ?? 0 },
  { label: "Upcoming bookings", value: (o) => o.upcomingBookings ?? 0 },
  { label: "Scheduled reminders", value: (o) => o.scheduledReminders ?? 0 },
  { label: "Follow-up", value: (o) => o.summary?.follow_up ?? 0 },
];

export function MetricCards({ overview }: MetricCardsProps) {
  return (
    <Grid container spacing={1.5}>
      {METRICS.map((metric) => (
        <Grid key={metric.label} size={{ xs: 6, sm: 4, md: 3 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Typography variant="caption" color="text.secondary">
                {metric.label}
              </Typography>
              <Typography variant="h5" sx={{ mt: 0.5 }}>
                {overview ? metric.value(overview) : "-"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

export default MetricCards;

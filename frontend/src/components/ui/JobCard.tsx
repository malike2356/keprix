"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import StatusPill from "@/components/ui/StatusPill";
import type { StatusKey } from "@/theme/tokens/status";

type JobCardProps = {
  id: string;
  name: string;
  schedule?: string;
  status: StatusKey;
  nextRunAt?: string | null;
  lastRunAt?: string | null;
  onClick?: () => void;
};

export default function JobCard({ id, name, schedule, status, nextRunAt, lastRunAt, onClick }: JobCardProps) {
  return (
    <Card variant="outlined" onClick={onClick} sx={{ cursor: onClick ? "pointer" : "default" }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            {name}
          </Typography>
          <StatusPill status={status} />
        </Box>
        <Typography variant="caption" color="text.secondary" display="block">
          {id}
        </Typography>
        {schedule && (
          <Typography variant="body2" sx={{ mt: 1 }}>
            Schedule: {schedule}
          </Typography>
        )}
        {nextRunAt && (
          <Typography variant="caption" color="text.secondary" display="block">
            Next run: {nextRunAt}
          </Typography>
        )}
        {lastRunAt && (
          <Typography variant="caption" color="text.secondary" display="block">
            Last run: {lastRunAt}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

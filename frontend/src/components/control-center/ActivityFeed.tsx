"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

type ActivityFeedProps = {
  activity: Array<Record<string, unknown>>;
  approvals: Array<Record<string, unknown>>;
  artifacts: Array<Record<string, unknown>>;
};

export default function ActivityFeed({ activity, approvals, artifacts }: ActivityFeedProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Activity and approvals
        </Typography>
        {approvals.length > 0 ? (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Pending approvals
            </Typography>
            {approvals.map((approval) => (
              <Chip
                key={String(approval.id)}
                size="small"
                color="warning"
                label={String(approval.reason || "Approval required")}
                sx={{ mr: 0.5, mb: 0.5 }}
              />
            ))}
          </Box>
        ) : null}
        {artifacts.length > 0 ? (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Recent artifacts
            </Typography>
            {artifacts.map((artifact) => (
              <Typography key={String(artifact.id)} variant="caption" display="block">
                {String(artifact.name)} ({String(artifact.path)})
              </Typography>
            ))}
          </Box>
        ) : null}
        {activity.map((entry) => (
          <Typography key={String(entry.id)} variant="body2" sx={{ mb: 0.5 }}>
            [{String(entry.type)}] {String(entry.message)}
          </Typography>
        ))}
      </CardContent>
    </Card>
  );
}

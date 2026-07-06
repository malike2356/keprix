"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

type Props = {
  overallScore?: number;
  recommendation?: string;
  growthStatus?: string;
};

export default function OpportunityScoreCard({ overallScore, recommendation, growthStatus }: Props) {
  return (
    <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { sm: "repeat(3, 1fr)" } }}>
      <Box sx={{ p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          Validation score
        </Typography>
        <Typography variant="h6">{overallScore != null ? `${overallScore.toFixed(1)}/100` : "n/a"}</Typography>
      </Box>
      <Box sx={{ p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          Recommendation
        </Typography>
        <Typography variant="body2">{recommendation ?? "Not scored yet"}</Typography>
      </Box>
      <Box sx={{ p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          Growth status
        </Typography>
        <Typography variant="body2">{growthStatus ?? "not started"}</Typography>
      </Box>
    </Box>
  );
}

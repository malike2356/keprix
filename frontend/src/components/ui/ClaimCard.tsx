"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import StatusPill from "@/components/ui/StatusPill";
import type { StatusKey } from "@/theme/tokens/status";

export type Claim = {
  id: string;
  text: string;
  confidence?: number;
  status?: StatusKey;
  sourceCount?: number;
};

type ClaimCardProps = {
  claim: Claim;
};

export default function ClaimCard({ claim }: ClaimCardProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 1 }}>
          <Typography variant="body1">{claim.text}</Typography>
          {claim.status ? <StatusPill status={claim.status} /> : null}
        </Box>
        <Box sx={{ display: "flex", gap: 2 }}>
          {claim.confidence !== undefined ? (
            <Typography variant="caption" color="text.secondary">
              Confidence {Math.round(claim.confidence * 100)}%
            </Typography>
          ) : null}
          {claim.sourceCount !== undefined ? (
            <Typography variant="caption" color="text.secondary">
              {claim.sourceCount} source{claim.sourceCount === 1 ? "" : "s"}
            </Typography>
          ) : null}
        </Box>
      </CardContent>
    </Card>
  );
}

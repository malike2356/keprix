"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import StatusPill from "@/components/ui/StatusPill";
import type { StatusKey } from "@/theme/tokens/status";

export type ApprovalCardData = {
  id: string;
  action: string;
  requester: string;
  target: string;
  dataTouched?: string;
  costImpact?: string;
  riskLevel?: "low" | "medium" | "high" | "critical";
  reversible?: boolean;
  expiresAt?: string;
  status?: StatusKey;
};

type ApprovalCardProps = {
  approval: ApprovalCardData;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onViewDetails?: (id: string) => void;
  disabled?: boolean;
};

function riskLabel(level: ApprovalCardData["riskLevel"]): string {
  if (!level) return "Unknown";
  return level.charAt(0).toUpperCase() + level.slice(1);
}

export default function ApprovalCard({
  approval,
  onApprove,
  onReject,
  onViewDetails,
  disabled = false,
}: ApprovalCardProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, mb: 2 }}>
          <Box>
            <Typography variant="subtitle1" fontWeight={600}>
              {approval.action}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Requested by {approval.requester}
            </Typography>
          </Box>
          {approval.status ? <StatusPill status={approval.status} /> : <StatusPill status="needs_approval" />}
        </Box>

        <Box sx={{ display: "grid", gap: 1, mb: 2 }}>
          <Typography variant="body2">
            <strong>Target:</strong> {approval.target}
          </Typography>
          {approval.dataTouched && (
            <Typography variant="body2">
              <strong>Data touched:</strong> {approval.dataTouched}
            </Typography>
          )}
          {approval.costImpact && (
            <Typography variant="body2">
              <strong>Cost impact:</strong> {approval.costImpact}
            </Typography>
          )}
          {approval.riskLevel && (
            <Typography variant="body2">
              <strong>Risk:</strong> {riskLabel(approval.riskLevel)}
            </Typography>
          )}
          {approval.reversible !== undefined && (
            <Typography variant="body2">
              <strong>Reversible:</strong> {approval.reversible ? "Yes" : "No"}
            </Typography>
          )}
          {approval.expiresAt && (
            <Typography variant="body2" color="text.secondary">
              Expires {approval.expiresAt}
            </Typography>
          )}
        </Box>

        <Divider sx={{ mb: 2 }} />

        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          <Button variant="contained" disabled={disabled} onClick={() => onApprove?.(approval.id)}>
            Approve
          </Button>
          <Button variant="outlined" color="inherit" disabled={disabled} onClick={() => onReject?.(approval.id)}>
            Reject
          </Button>
          {onViewDetails && (
            <Button variant="text" onClick={() => onViewDetails(approval.id)}>
              View details
            </Button>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

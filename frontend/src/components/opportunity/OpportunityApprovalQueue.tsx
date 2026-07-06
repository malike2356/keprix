"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { approveOpportunityAction } from "@/lib/opportunity-api";

type ApprovalRow = {
  approval_id: string;
  action: string;
  reason?: string;
  metadata?: {
    preview?: string;
    integration?: string;
    risk_level?: string;
  };
};

type Props = {
  opportunityId: string;
  approvals: ApprovalRow[];
  onUpdated: () => void;
};

export default function OpportunityApprovalQueue({ opportunityId, approvals, onUpdated }: Props) {
  const handleApprove = async (approvalId: string, approved: boolean) => {
    await approveOpportunityAction(opportunityId, approvalId, approved);
    onUpdated();
  };

  if (!approvals.length) {
    return <Typography variant="body2">No pending approvals.</Typography>;
  }

  return (
    <Stack spacing={1.5}>
      {approvals.map((row) => (
        <Box key={row.approval_id} sx={{ p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="subtitle2">{row.action}</Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            Risk: {row.metadata?.risk_level ?? "medium"} | Integration: {row.metadata?.integration ?? "n/a"}
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            {row.metadata?.preview ?? row.reason ?? "No preview"}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Button size="small" variant="contained" onClick={() => handleApprove(row.approval_id, true)}>
              Approve
            </Button>
            <Button size="small" variant="outlined" onClick={() => handleApprove(row.approval_id, false)}>
              Reject
            </Button>
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}

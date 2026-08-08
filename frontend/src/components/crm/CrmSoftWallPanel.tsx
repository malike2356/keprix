"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import {
  approveCrmApproval,
  fetchCrmApprovals,
  rejectCrmApproval,
} from "@/lib/crm-api";
import { CRM_WORKSPACE, type CrmApproval } from "@/components/crm/types";

type CrmSoftWallPanelProps = {
  workspaceId?: string;
  title?: string;
};

export function CrmSoftWallPanel({
  workspaceId = CRM_WORKSPACE,
  title = "Soft Wall CRM approvals",
}: CrmSoftWallPanelProps) {
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);

  const approvals = useSWR(["crm-approvals", workspaceId], () => fetchCrmApprovals(workspaceId));

  const act = async (id: string, action: "approve" | "reject") => {
    setBusyId(id);
    setError(null);
    try {
      if (action === "approve") await approveCrmApproval(id, workspaceId);
      else await rejectCrmApproval(id, workspaceId);
      setMessage(action === "approve" ? "CRM action approved" : "CRM action rejected");
      await approvals.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action}`);
    } finally {
      setBusyId(null);
    }
  };

  const items: CrmApproval[] = approvals.data?.items ?? [];

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Pending CRM Soft Wall items (enrich, enroll, merge, stage, kill switch). Approve or reject here.
        </Typography>

        {error ? (
          <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        ) : null}
        {message ? (
          <Alert severity="success" sx={{ mb: 1.5 }} onClose={() => setMessage(null)}>
            {message}
          </Alert>
        ) : null}

        {approvals.isLoading && !approvals.data ? (
          <Typography color="text.secondary">Loading approvals...</Typography>
        ) : items.length === 0 ? (
          <Typography color="text.secondary">No pending Soft Wall CRM approvals.</Typography>
        ) : (
          <Stack spacing={1.5}>
            {items.map((item) => (
              <Card key={item.id} variant="outlined">
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Stack direction="row" justifyContent="space-between" spacing={1} flexWrap="wrap" useFlexGap>
                    <Typography variant="body2" fontWeight={600}>
                      {item.subject || item.kind || item.id}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.kind || "crm"}
                      {item.object_type ? ` · ${item.object_type}` : ""}
                      {item.object_id ? ` · ${item.object_id}` : ""}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                    <Button
                      size="small"
                      variant="contained"
                      disabled={busyId === item.id}
                      onClick={() => void act(item.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={busyId === item.id}
                      onClick={() => void act(item.id, "reject")}
                    >
                      Reject
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

export default CrmSoftWallPanel;

"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import CrmStatusBadge from "@/components/crm/visual/CrmStatusBadge";
import { fetchCrmWorkflows, setCrmWorkflowStatus } from "@/lib/crm-api";

export default function CrmWorkflowsPage() {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const workflows = useSWR(["crm-workflows", CRM_WORKSPACE], () => fetchCrmWorkflows(CRM_WORKSPACE));

  const setStatus = async (id: string, status: string) => {
    setError(null);
    try {
      await setCrmWorkflowStatus(id, status, CRM_WORKSPACE);
      setMessage(`Workflow ${status}`);
      await workflows.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Workflow canvas is the Must visual authoring surface (prompt 508; satisfies Nice 451 scope). Open a workflow to
        inspect nodes, validate, simulate, and publish. Soft Wall sequences remain the send runtime.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      {workflows.isLoading ? (
        <Typography color="text.secondary">Loading workflows...</Typography>
      ) : (workflows.data?.items || []).length === 0 ? (
        <Typography color="text.secondary">No sequences yet. Open Soft Wall to create one.</Typography>
      ) : (
        <Stack spacing={1}>
          {(workflows.data?.items || []).map((wf) => (
            <Card key={String(wf.id)} variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography variant="body2" fontWeight={600}>
                    {String(wf.name || wf.id)}
                  </Typography>
                  <CrmStatusBadge state={String(wf.status || "active")} />
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  enrolls {String(wf.enroll_count ?? 0)} · steps {Array.isArray(wf.steps) ? wf.steps.length : 0}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                  <Button size="small" variant="contained" component={Link} href={`/crm/workflows/${wf.id}`}>
                    Open canvas
                  </Button>
                  <Button size="small" onClick={() => void setStatus(String(wf.id), "active")}>
                    Activate
                  </Button>
                  <Button size="small" onClick={() => void setStatus(String(wf.id), "paused")}>
                    Pause
                  </Button>
                  <Button size="small" onClick={() => void setStatus(String(wf.id), "draft")}>
                    Draft
                  </Button>
                  <Button size="small" component={Link} href={String(wf.deep_link || "/outreach")}>
                    Soft Wall sequence
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}
    </Stack>
  );
}

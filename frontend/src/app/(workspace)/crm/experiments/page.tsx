"use client";

import Alert from "@mui/material/Alert";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function fetchExperiments() {
  const res = await ceApi(`/api/crm/experiments?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Experiments failed"));
  return res.json();
}

export default function CrmExperimentsPage() {
  const data = useSWR(["crm-experiments", CRM_WORKSPACE], fetchExperiments);
  return (
    <Stack spacing={2} sx={{ maxWidth: 900 }}>
      <Typography variant="body2" color="text.secondary">
        Template A/B experiments with sticky cohorts, min-sample warnings, and Soft Wall winner promote.
      </Typography>
      {data.error ? <Alert severity="error">{String(data.error.message || data.error)}</Alert> : null}
      {(data.data?.items || []).map((exp: { id: string; name: string; status: string; min_sample?: number }) => (
        <Card key={exp.id} variant="outlined">
          <CardContent>
            <Typography variant="subtitle1">{exp.name}</Typography>
            <Typography variant="body2" color="text.secondary">
              Status: {exp.status} | min sample: {exp.min_sample ?? 50}
            </Typography>
          </CardContent>
        </Card>
      ))}
      {!data.data?.items?.length ? (
        <Typography variant="body2" color="text.secondary">
          No experiments yet. Create via POST /api/crm/experiments.
        </Typography>
      ) : null}
    </Stack>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function fetchReport() {
  const res = await ceApi(`/api/crm/attribution/report?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Attribution failed"));
  return res.json();
}

async function fetchMatrix() {
  const res = await ceApi(`/api/crm/nice/matrix`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Matrix failed"));
  return res.json();
}

export default function CrmAttributionPage() {
  const report = useSWR(["crm-attr", CRM_WORKSPACE], fetchReport);
  const matrix = useSWR(["crm-nice-matrix"], fetchMatrix);
  const byMode = report.data?.by_mode || {};

  return (
    <Stack spacing={2} sx={{ maxWidth: 900 }}>
      <Typography variant="body2" color="text.secondary">
        Attribution modes sourced / influenced / closed. Vanity-send-only closed deals are excluded. No Stripe prices created.
      </Typography>
      {report.error ? <Alert severity="error">{String(report.error.message || report.error)}</Alert> : null}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Pipeline by mode</Typography>
          {Object.entries(byMode).map(([mode, info]) => (
            <Typography key={mode} variant="body2">
              {mode}: {(info as { count?: number; amount?: number }).count ?? 0} deals /{" "}
              {(info as { amount?: number }).amount ?? 0}
            </Typography>
          ))}
          <Typography variant="body2" sx={{ mt: 1 }}>
            Cost per qualified opportunity: {report.data?.cost_per_qualified_opportunity ?? "-"}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            Vanity excluded: {report.data?.vanity_excluded ?? 0}
          </Typography>
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Nice wave matrix</Typography>
          <StructuredDataView value={matrix.data?.prompts || {}} />
          <Typography variant="caption" color="text.secondary">
            {matrix.data?.docs}
          </Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}

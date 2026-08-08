"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function fetchQuality() {
  const res = await ceApi(`/api/crm/data-quality?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Quality failed"));
  return res.json();
}

export default function CrmDataQualityPage() {
  const [message, setMessage] = React.useState<string | null>(null);
  const [detail, setDetail] = React.useState<unknown>(null);
  const data = useSWR(["crm-dq", CRM_WORKSPACE], fetchQuality);
  const counts = data.data?.counts || {};

  const reverify = async () => {
    setMessage(null);
    setDetail(null);
    const res = await ceApi(`/api/crm/data-quality/reverify?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const payload = await res.json();
    if (payload.blocked) {
      setMessage(`Soft Wall required: ${payload.approval?.id || ""}`);
      return;
    }
    if (payload.ok) {
      setMessage(`Queued ${payload.job_id}`);
    } else {
      setMessage(parseApiErrorMessage(payload, "Re-verify failed"));
      setDetail(payload);
    }
    await data.mutate();
  };

  return (
    <Stack spacing={2} sx={{ maxWidth: 900 }}>
      <Typography variant="body2" color="text.secondary">
        Completeness, staleness, conflicts, and unverified inference. Bulk re-verify is Soft Wall gated.
      </Typography>
      {data.error ? <Alert severity="error">{String(data.error.message || data.error)}</Alert> : null}
      {message ? <Alert severity="info">{message}</Alert> : null}
      {detail ? <StructuredDataView value={detail} /> : null}
      {data.data?.alert ? <Alert severity="warning">{data.data.alert_message}</Alert> : null}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Summary</Typography>
          <Typography variant="body2">Incomplete email: {counts.incomplete_email ?? 0}</Typography>
          <Typography variant="body2">Incomplete phone: {counts.incomplete_phone ?? 0}</Typography>
          <Typography variant="body2">Conflicts: {counts.conflicts ?? 0}</Typography>
          <Typography variant="body2">Stale: {counts.stale ?? 0} ({data.data?.stale_pct ?? 0}%)</Typography>
          <Button sx={{ mt: 1 }} variant="outlined" onClick={() => void reverify()}>
            Re-verify (Soft Wall)
          </Button>
        </CardContent>
      </Card>
    </Stack>
  );
}

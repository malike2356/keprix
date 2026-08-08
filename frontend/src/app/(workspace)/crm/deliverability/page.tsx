"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { fetchCrmDeliverability } from "@/lib/crm-api";

export default function CrmDeliverabilityPage() {
  const data = useSWR(["crm-deliverability", CRM_WORKSPACE], () => fetchCrmDeliverability(CRM_WORKSPACE));
  const snap = data.data;

  return (
    <Stack spacing={2} sx={{ maxWidth: 800 }}>
      <Typography variant="body2" color="text.secondary">
        Sender readiness is a hard gate before first cold campaign Soft Wall enroll.
      </Typography>
      {data.error ? <Alert severity="error">Could not load deliverability</Alert> : null}
      {snap?.soft_wall_block_cold_send ? (
        <Alert severity="warning">
          Cold send blocked: {String(snap.soft_wall_block_reason || "checklist incomplete")}
        </Alert>
      ) : (
        <Alert severity="success">Cold send Soft Wall gate clear (or not yet blocking).</Alert>
      )}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Rates (honest zeros when empty)</Typography>
          <Typography variant="body2" color="text.secondary">
            bounce {String(snap?.rates?.bounce_rate_pct ?? 0)}% · complaint{" "}
            {String(snap?.rates?.complaint_rate_pct ?? 0)}% · unsubscribe{" "}
            {String(snap?.rates?.unsubscribe_rate_pct ?? 0)}%
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Breaches: {(snap?.breaches || []).join(", ") || "none"}
          </Typography>
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Checklist</Typography>
          {Object.entries(snap?.checklist || {}).map(([k, v]) => (
            <Typography key={k} variant="body2" color="text.secondary">
              {k}: {v ? "ok" : "missing"}
            </Typography>
          ))}
        </CardContent>
      </Card>
      <Button size="small" component={Link} href="/crm/settings">
        Kill switches and cadence
      </Button>
    </Stack>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { fetchCrmOpsCentre } from "@/lib/crm-api";

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="subtitle2" gutterBottom>
          {title}
        </Typography>
        {children}
      </CardContent>
    </Card>
  );
}

export default function CrmOpsCentre() {
  const ops = useSWR(["crm-ops", CRM_WORKSPACE], () => fetchCrmOpsCentre(CRM_WORKSPACE), {
    refreshInterval: 5000,
  });

  const panels = (ops.data?.panels || {}) as Record<string, unknown>;
  const alerts = ops.data?.alerts || [];
  const transport = ops.data?.transport || {};
  const lastUpdated = String(transport.last_updated || ops.data?.generated_at || "");

  const listOrEmpty = (value: unknown): Array<Record<string, unknown>> =>
    Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h6">Operations centre</Typography>
        <Typography variant="body2" color="text.secondary">
          Supervise active runs, Soft Wall approvals, replies, failures, deliverability, and kill switches.
        </Typography>
      </Box>

      <Alert severity={transport.degraded ? "warning" : "info"}>
        Transport: {String(transport.preferred || "polling")} · last updated {lastUpdated || "..."}. Real-time outage
        degrades to visible polling; dashboards never pretend to be live when stale.
      </Alert>

      {ops.error ? <Alert severity="error">Could not load ops centre</Alert> : null}

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Alerts
        </Typography>
        {alerts.length === 0 ? (
          <Typography color="text.secondary">No active high-severity alerts.</Typography>
        ) : (
          <Stack spacing={1}>
            {alerts.map((a) => (
              <Card key={String(a.id)} variant="outlined">
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Chip size="small" label={String(a.severity || "info")} color={a.severity === "high" ? "error" : "warning"} />
                    <Typography variant="body2" fontWeight={600}>
                      {String(a.label)}
                    </Typography>
                    {a.href ? (
                      <Typography component={Link} href={String(a.href)} variant="caption" color="primary">
                        Open evidence
                      </Typography>
                    ) : null}
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    Acknowledgement never dismisses the underlying problem.
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}
      </Box>

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Panel title="Active runs">
            {listOrEmpty(panels.active_runs).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                None
              </Typography>
            ) : (
              listOrEmpty(panels.active_runs).map((r) => (
                <Typography key={String(r.id)} component={Link} href={String(r.href)} display="block" variant="body2" color="primary">
                  {String(r.id)} · {String(r.status)}
                </Typography>
              ))
            )}
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Panel title="Waiting approvals">
            {listOrEmpty(panels.waiting_approvals).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                None
              </Typography>
            ) : (
              listOrEmpty(panels.waiting_approvals).map((a) => (
                <Typography key={String(a.id)} component={Link} href={String(a.href || "/crm")} display="block" variant="body2" color="primary">
                  {String(a.subject || a.id)}
                </Typography>
              ))
            )}
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Panel title="Failed nodes">
            {listOrEmpty(panels.failed_nodes).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                None
              </Typography>
            ) : (
              listOrEmpty(panels.failed_nodes).map((n) => (
                <Typography key={`${n.run_id}-${n.node_id}`} component={Link} href={String(n.href)} display="block" variant="body2" color="primary">
                  {String(n.label || n.node_id)} ({String(n.run_id)})
                </Typography>
              ))
            )}
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Panel title="Deliverability guardrails">
            <Typography variant="body2">
              Block cold send: {String((panels.deliverability_guardrails as { block_cold_send?: boolean } | undefined)?.block_cold_send ?? false)}
            </Typography>
            <Typography component={Link} href="/crm/deliverability" variant="caption" color="primary">
              Open deliverability
            </Typography>
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Panel title="Kill switches">
            {listOrEmpty(panels.kill_switches).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                None configured
              </Typography>
            ) : (
              listOrEmpty(panels.kill_switches).map((k, idx) => (
                <Typography key={String(k.id || idx)} variant="body2">
                  {String(k.scope)} · enabled={String(k.enabled)}
                </Typography>
              ))
            )}
            <Typography component={Link} href="/crm/settings" variant="caption" color="primary">
              Settings
            </Typography>
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Panel title="New replies / human takeover">
            <Typography variant="body2" color="text.secondary">
              Replies: {listOrEmpty(panels.new_replies).length} · Takeover: {listOrEmpty(panels.human_takeover).length}
            </Typography>
            <Typography component={Link} href="/crm/inbox" variant="caption" color="primary">
              Open inbox
            </Typography>
          </Panel>
        </Grid>
      </Grid>

      <Typography variant="caption" color="text.secondary">
        Telegram actions remain signed, expiring, and single-use via Soft Wall. Sensitive detail stays in authenticated
        web. Presence is advisory only.
      </Typography>
    </Stack>
  );
}

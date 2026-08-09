"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import dynamic from "next/dynamic";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchAivaAnalyticsOutreach,
  fetchAivaAnalyticsOverview,
  fetchAivaAnalyticsUsage,
  fetchAivaAnalyticsWorker,
  type AnalyticsPeriodDays,
} from "@/lib/aiva-analytics-api";

const ReactApexChart = dynamic(() => import("react-apexcharts"), { ssr: false });

type Surface = "aiva" | "admin";

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return ";";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const rem = Math.round(seconds % 60);
  if (minutes < 60) return rem ? `${minutes}m ${rem}s` : `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

function formatPct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
        <Typography variant="h5" fontWeight={700}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          {label}
        </Typography>
        {hint ? (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
            {hint}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
}

function PeriodSelector({
  value,
  onChange,
}: {
  value: AnalyticsPeriodDays;
  onChange: (value: AnalyticsPeriodDays) => void;
}) {
  return (
    <ButtonGroup size="small" variant="outlined">
      {([7, 30, 90] as AnalyticsPeriodDays[]).map((days) => (
        <Button
          key={days}
          variant={value === days ? "contained" : "outlined"}
          onClick={() => onChange(days)}
        >
          {days} days
        </Button>
      ))}
    </ButtonGroup>
  );
}

export default function AivaAnalyticsDashboard() {
  const [period, setPeriod] = React.useState<AnalyticsPeriodDays>(30);
  const [surface, setSurface] = React.useState<Surface>("aiva");
  const workspaceId = "default";

  const overview = useSWR(["aiva-analytics-overview", period, workspaceId], () =>
    fetchAivaAnalyticsOverview(period, workspaceId),
  );
  const usage = useSWR(["aiva-analytics-usage", period, workspaceId], () =>
    fetchAivaAnalyticsUsage(period, workspaceId),
  );
  const outreach = useSWR(["aiva-analytics-outreach", period, workspaceId], () =>
    fetchAivaAnalyticsOutreach(period, workspaceId),
  );
  const worker = useSWR(["aiva-analytics-worker", period, workspaceId], () =>
    fetchAivaAnalyticsWorker(period, workspaceId),
  );

  const error =
    overview.error?.message ||
    usage.error?.message ||
    outreach.error?.message ||
    worker.error?.message ||
    null;

  const ov = overview.data;
  const us = usage.data;
  const out = outreach.data;
  const wk = worker.data;

  const series = us?.series ?? [];
  const inboundOutbound = {
    categories: series.map((row) => row.day),
    inbound: series.map((row) => row.worker_messages || row.emails_sent || 0),
    outbound: series.map((row) => row.replies || row.agent_calls || 0),
  };

  const mixTotal =
    (us?.totals.worker_messages || 0) + (us?.totals.replies || 0) || 1;
  const inboundShare = Math.round(((us?.totals.worker_messages || 0) / mixTotal) * 100);
  const outboundShare = 100 - inboundShare;

  return (
    <Box>
      <PageHeader
        title="Analytics"
        description="Aiva conversation metrics and workspace ops (agent calls, outreach, escalations, usage)."
        actions={
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <ButtonGroup size="small" variant="outlined">
              <Button
                variant={surface === "aiva" ? "contained" : "outlined"}
                onClick={() => setSurface("aiva")}
              >
                Aiva
              </Button>
              <Button
                variant={surface === "admin" ? "contained" : "outlined"}
                onClick={() => setSurface("admin")}
              >
                Admin
              </Button>
            </ButtonGroup>
            <PeriodSelector value={period} onChange={setPeriod} />
          </Stack>
        }
      />

      {error ? (
        <Typography color="error" variant="body2" sx={{ mb: 2 }}>
          {/bearer|authentication required|expired session/i.test(error) ? (
            <>
              {error}.{" "}
              <Link component="a" href="/auth/login">
                Sign in
              </Link>{" "}
              and reload this page.
            </>
          ) : (
            error
          )}
        </Typography>
      ) : null}

      {surface === "aiva" ? (
        <>
          <Grid container spacing={1.5} sx={{ mb: 2 }}>
            <Grid size={{ xs: 6, md: 2 }}>
              <StatCard
                label="Total conversations"
                value={ov?.agent.calls ?? ";"}
                hint="Agent turns in period"
              />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <StatCard
                label="Aiva replies"
                value={ov?.workers.messages ?? ";"}
                hint="Worker messages"
              />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <StatCard
                label="Escalation rate"
                value={
                  ov && ov.agent.calls
                    ? formatPct(ov.workers.escalations / Math.max(ov.agent.calls, 1))
                    : "0.0%"
                }
              />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <StatCard
                label="Avg first response"
                value={formatDuration(ov?.agent.avg_duration_seconds ?? 0)}
                hint="Mean agent duration"
              />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <StatCard
                label="Tokens used"
                value={ov?.agent.tokens ?? ";"}
                hint={`Cost ~$${(ov?.agent.estimated_cost_usd ?? 0).toFixed(4)}`}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <StatCard
                label="Tool calls"
                value={ov?.agent.tool_calls ?? ";"}
                hint={`${ov?.agent.errors ?? 0} errors`}
              />
            </Grid>
          </Grid>

          <Grid container spacing={1.5} sx={{ mb: 2 }}>
            <Grid size={{ xs: 6, md: 3 }}>
              <StatCard
                label="Usage this period"
                value={ov?.agent.calls ?? ";"}
                hint="Agent calls (workspace)"
              />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <StatCard
                label="Outreach sent"
                value={ov?.outreach.emails_sent ?? ";"}
                hint={`Reply rate ${formatPct(ov?.outreach.reply_rate ?? 0)}`}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <StatCard
                label="Open escalations"
                value={ov?.workers.escalations ?? ";"}
                hint="Worker escalations in period"
              />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <StatCard
                label="Inbound / outbound"
                value={`${us?.totals.worker_messages ?? 0} / ${us?.totals.replies ?? 0}`}
                hint="Messages vs replies"
              />
            </Grid>
          </Grid>

          <Grid container spacing={1.5} sx={{ mb: 2 }}>
            <Grid size={{ xs: 12, md: 8 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom>
                    Inbound vs outbound
                  </Typography>
                  {series.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No time-series data yet. Agent and outreach traffic will appear here as metrics flow in.
                    </Typography>
                  ) : (
                    <ReactApexChart
                      type="area"
                      height={280}
                      series={[
                        { name: "Inbound", data: inboundOutbound.inbound },
                        { name: "Outbound", data: inboundOutbound.outbound },
                      ]}
                      options={{
                        chart: { toolbar: { show: false }, background: "transparent" },
                        dataLabels: { enabled: false },
                        stroke: { curve: "smooth", width: 2 },
                        fill: { type: "gradient", gradient: { opacityFrom: 0.35, opacityTo: 0.05 } },
                        xaxis: { categories: inboundOutbound.categories },
                        legend: { position: "top" },
                        colors: ["#1a5f7a", "#f59e0b"],
                      }}
                    />
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Stack spacing={1.5}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom>
                      Message direction mix
                    </Typography>
                    <ReactApexChart
                      type="donut"
                      height={220}
                      series={[inboundShare, outboundShare]}
                      options={{
                        labels: ["Inbound", "Outbound"],
                        colors: ["#1a5f7a", "#f59e0b"],
                        legend: { position: "bottom" },
                        dataLabels: { enabled: false },
                      }}
                    />
                  </CardContent>
                </Card>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom>
                      Escalation status
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip
                        color={(ov?.workers.escalations ?? 0) > 0 ? "warning" : "success"}
                        label={(ov?.workers.escalations ?? 0) > 0 ? "Has escalations" : "Stable"}
                        size="small"
                      />
                      <Typography variant="body2" color="text.secondary">
                        {ov?.workers.escalations ?? 0} in period
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Stack>
            </Grid>
          </Grid>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Outreach funnel
              </Typography>
              <Grid container spacing={1.5}>
                <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                  <StatCard label="Emails sent" value={out?.funnel.emails_sent ?? 0} />
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                  <StatCard label="Opened" value={out?.funnel.emails_opened ?? 0} hint={formatPct(out?.funnel.open_rate ?? 0)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                  <StatCard label="Clicked" value={out?.funnel.emails_clicked ?? 0} hint={formatPct(out?.funnel.click_rate ?? 0)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                  <StatCard label="Replies" value={out?.funnel.replies ?? 0} hint={formatPct(out?.funnel.reply_rate ?? 0)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                  <StatCard label="Bookings" value={out?.funnel.bookings ?? 0} hint={formatPct(out?.funnel.booking_rate ?? 0)} />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </>
      ) : (
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 6, md: 3 }}>
            <StatCard label="Agent calls" value={ov?.agent.calls ?? 0} />
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <StatCard label="Tool calls" value={ov?.agent.tool_calls ?? 0} />
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <StatCard label="Worker messages" value={wk?.messages ?? 0} />
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <StatCard
              label="Est. cost (USD)"
              value={(ov?.agent.estimated_cost_usd ?? 0).toFixed(4)}
              hint={`Avg duration ${formatDuration(wk?.avg_duration_seconds ?? 0)}`}
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Admin ops in Keprix currently focuses on agent runtime, outreach, and worker
                  escalations. For LLM spend detail use LLM usage; for traces use Observability.
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Button component="a" href="/data?tab=usage" size="small" variant="outlined">
                    LLM usage
                  </Button>
                  <Button component="a" href="/data?tab=observability" size="small" variant="outlined">
                    Observability
                  </Button>
                  <Button component="a" href="/data?tab=analytics" size="small" variant="outlined">
                    Data analysis notebook
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
        Looking for CSV/Python charts? That lives under{" "}
        <Link component="a" href="/data?tab=analytics">
          Data analysis
        </Link>
        .
      </Typography>
    </Box>
  );
}

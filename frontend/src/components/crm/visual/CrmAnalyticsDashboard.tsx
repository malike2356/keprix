"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid2";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { backfillCrmMetrics, queryCrmMetrics } from "@/lib/crm-api";

function fmt(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4);
  return String(value);
}

export default function CrmAnalyticsDashboard() {
  const [days, setDays] = React.useState(30);
  const [cohort, setCohort] = React.useState("first_touch");
  const [attribution, setAttribution] = React.useState("sourced");
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  const metrics = useSWR(["crm-metrics", CRM_WORKSPACE, days, cohort, attribution], () =>
    queryCrmMetrics({ days, cohort, attribution }, CRM_WORKSPACE),
  );

  const backfill = async () => {
    setError(null);
    try {
      const res = await backfillCrmMetrics(CRM_WORKSPACE);
      setMessage(`Backfill wrote ${String(res.wrote)} events; gaps ${String(res.gap_count)}`);
      await metrics.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backfill failed");
    }
  };

  const measures = metrics.data?.measures || {};
  const guards = metrics.data?.guards || {};
  const funnel = metrics.data?.funnel || [];

  const kpiKeys = [
    "unique_leads",
    "pipeline",
    "revenue",
    "positive_reply_rate",
    "booking_rate",
    "win_rate",
    "cost_per_qualified_lead",
    "cycle_time",
  ];

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1}>
        <Box>
          <Typography variant="h6">CRM analytics</Typography>
          <Typography variant="body2" color="text.secondary">
            Decision-grade charts from the semantic layer. Drill into{" "}
            <Typography component="a" href="/crm/pipeline" color="primary" variant="body2">
              pipeline
            </Typography>{" "}
            or{" "}
            <Typography component="a" href="/crm/leads" color="primary" variant="body2">
              leads
            </Typography>
            .
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel id="days">Days</InputLabel>
            <Select labelId="days" label="Days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              {[7, 30, 90].map((d) => (
                <MenuItem key={d} value={d}>
                  {d}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="cohort">Cohort</InputLabel>
            <Select labelId="cohort" label="Cohort" value={cohort} onChange={(e) => setCohort(e.target.value)}>
              <MenuItem value="first_touch">First touch</MenuItem>
              <MenuItem value="enrollment">Enrollment</MenuItem>
              <MenuItem value="opportunity_created">Opportunity</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="attr">Attribution</InputLabel>
            <Select
              labelId="attr"
              label="Attribution"
              value={attribution}
              onChange={(e) => setAttribution(e.target.value)}
            >
              <MenuItem value="sourced">Sourced</MenuItem>
              <MenuItem value="influenced">Influenced</MenuItem>
              <MenuItem value="multi_touch">Multi-touch</MenuItem>
            </Select>
          </FormControl>
          <Button size="small" variant="outlined" onClick={() => void backfill()}>
            Backfill events
          </Button>
        </Stack>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      {metrics.data?.incomplete_history ? (
        <Alert severity="warning">
          Incomplete history labelled honestly. Definition {metrics.data.definition_version}. Freshness{" "}
          {metrics.data.freshness}. {metrics.data.cohort_label}. {metrics.data.attribution_label}.
        </Alert>
      ) : metrics.data ? (
        <Alert severity="info">
          Definition {metrics.data.definition_version} · Freshness {metrics.data.freshness} ·{" "}
          {metrics.data.cohort_label} · {metrics.data.attribution_label}
        </Alert>
      ) : null}

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Executive overview
        </Typography>
        {metrics.isLoading && !metrics.data ? (
          <Typography color="text.secondary">Loading metrics...</Typography>
        ) : (
          <Grid container spacing={1.5}>
            {kpiKeys.map((key) => {
              const row = measures[key] || {};
              return (
                <Grid key={key} size={{ xs: 6, sm: 4, md: 3 }}>
                  <Card variant="outlined">
                    <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                      <Typography variant="caption" color="text.secondary">
                        {key.replace(/_/g, " ")}
                      </Typography>
                      <Typography variant="h5" sx={{ mt: 0.5 }}>
                        {fmt(row.value)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        num {fmt(row.numerator)}
                        {row.denominator != null ? ` / den ${fmt(row.denominator)}` : ""}
                        {row.incomplete ? " · incomplete" : ""}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        )}
      </Box>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Funnel
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          discovered to paying with conversion and denominator tooltips in the table.
        </Typography>
        <Table size="small" aria-label="Funnel table">
          <TableHead>
            <TableRow>
              <TableCell>Step</TableCell>
              <TableCell align="right">Count</TableCell>
              <TableCell align="right">Conversion from prev</TableCell>
              <TableCell align="right">Prev denominator</TableCell>
              <TableCell>Drill-down</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {funnel.map((step) => (
              <TableRow key={String(step.step)}>
                <TableCell>{String(step.step)}</TableCell>
                <TableCell align="right">{fmt(step.count)}</TableCell>
                <TableCell align="right">{fmt(step.conversion_from_prev)}</TableCell>
                <TableCell align="right">{fmt(step.denominator_prev)}</TableCell>
                <TableCell>
                  <Typography
                    component="a"
                    href={`/crm/pipeline?stage=${encodeURIComponent(String(step.step === "replied" ? "engaged" : step.step === "contactable" ? "approved" : step.step))}`}
                    variant="caption"
                    color="primary"
                  >
                    Open filtered board
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Guard metrics
        </Typography>
        <Table size="small" aria-label="Guard metrics">
          <TableHead>
            <TableRow>
              <TableCell>Guard</TableCell>
              <TableCell align="right">Rate</TableCell>
              <TableCell align="right">Numerator</TableCell>
              <TableCell align="right">Denominator</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(guards).map(([id, row]) => (
              <TableRow key={id}>
                <TableCell>{id.replace(/_/g, " ")}</TableCell>
                <TableCell align="right">{fmt(row.value)}</TableCell>
                <TableCell align="right">{fmt(row.numerator)}</TableCell>
                <TableCell align="right">{fmt(row.denominator)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Typography variant="caption" color="text.secondary">
        Must-thin: KPI cards + accessible tables ship first. Sankey/heatmap polish can deepen later without changing
        semantic definitions. Opens/clicks are not core truth.
      </Typography>
    </Stack>
  );
}

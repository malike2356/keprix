"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import {
  exportObservabilityTrace,
  fetchObservabilityDashboard,
  fetchObservabilityTrace,
  fetchObservabilityTraces,
  type ObservabilitySpan,
  type ObservabilityTrace,
} from "@/lib/observability-api";

type RefreshMode = "off" | "5" | "15";

function traceId(trace: ObservabilityTrace): string {
  return String(trace.run_id || trace.id || "");
}

function formatMs(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "-";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

function SpanWaterfall({ spans }: { spans: ObservabilitySpan[] }) {
  const maxEnd = Math.max(...spans.map((span) => span.offset_ms + span.duration_ms), 1);
  const colorFor = (kind: string) => {
    if (kind === "error") return "error.main";
    if (kind === "tool") return "info.main";
    if (kind === "model") return "secondary.main";
    if (kind === "node") return "primary.main";
    return "text.secondary";
  };

  if (spans.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No span timeline available for this run.
      </Typography>
    );
  }

  return (
    <Stack spacing={1}>
      {spans.map((span, index) => (
        <Box key={`${span.kind}-${span.name}-${index}`}>
          <Stack direction="row" justifyContent="space-between" spacing={1}>
            <Typography variant="caption">
              {span.kind}: {span.name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatMs(span.duration_ms)}
            </Typography>
          </Stack>
          <Box sx={{ position: "relative", height: 10, bgcolor: "action.hover", borderRadius: 1 }}>
            <Box
              sx={{
                position: "absolute",
                left: `${(span.offset_ms / maxEnd) * 100}%`,
                width: `${Math.max(2, (span.duration_ms / maxEnd) * 100)}%`,
                height: "100%",
                bgcolor: colorFor(span.kind),
                borderRadius: 1,
              }}
            />
          </Box>
        </Box>
      ))}
    </Stack>
  );
}

export default function ObservabilityPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = React.useState(searchParams.get("status") || "");
  const [agent, setAgent] = React.useState(searchParams.get("agent") || "");
  const [q, setQ] = React.useState(searchParams.get("q") || "");
  const [refresh, setRefresh] = React.useState<RefreshMode>(
    (searchParams.get("refresh") as RefreshMode) || "15",
  );
  const [selectedId, setSelectedId] = React.useState<string | null>(searchParams.get("trace") || null);
  const [drawerError, setDrawerError] = React.useState<string | null>(null);
  const [exportMessage, setExportMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    setStatus(searchParams.get("status") || "");
    setAgent(searchParams.get("agent") || "");
    setQ(searchParams.get("q") || "");
    setRefresh((searchParams.get("refresh") as RefreshMode) || "15");
    setSelectedId(searchParams.get("trace"));
  }, [searchParams]);

  const replaceParams = React.useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (!value) next.delete(key);
        else next.set(key, value);
      }
      next.set("tab", "observability");
      router.replace(`/data?${next.toString()}`);
    },
    [router, searchParams],
  );

  const refreshInterval =
    refresh === "off" ? 0 : refresh === "5" ? 5000 : 15000;

  const {
    data: dashboard,
    error: dashError,
    isLoading: dashLoading,
  } = useSWR("observability-dashboard", fetchObservabilityDashboard, {
    refreshInterval: refreshInterval || undefined,
  });

  const filters = React.useMemo(
    () => ({
      limit: 80,
      status: status || undefined,
      agent: agent || undefined,
      q: q || undefined,
    }),
    [status, agent, q],
  );

  const {
    data: traces = [],
    error: tracesError,
    isLoading: tracesLoading,
  } = useSWR(["observability-traces", filters], () => fetchObservabilityTraces(filters), {
    refreshInterval: refreshInterval || undefined,
  });

  const {
    data: selectedTrace,
    isLoading: selectedLoading,
  } = useSWR(selectedId ? ["observability-trace", selectedId] : null, () =>
    fetchObservabilityTrace(selectedId as string),
  );

  const runtime = dashboard?.runtime;
  const otelOk = Boolean(dashboard?.otel_configured ?? runtime?.otel_configured);

  const openTrace = (id: string) => {
    setDrawerError(null);
    setExportMessage(null);
    replaceParams({ trace: id });
  };

  const closeTrace = () => {
    replaceParams({ trace: null });
  };

  const handleExport = async (id: string) => {
    setDrawerError(null);
    setExportMessage(null);
    try {
      const payload = await exportObservabilityTrace(id);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `trace-${id}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setExportMessage("Trace export downloaded.");
    } catch (err) {
      setDrawerError(err instanceof Error ? err.message : "Export failed");
    }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2, flexWrap: "wrap" }}>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={refresh}
          onChange={(_event, next: RefreshMode | null) => {
            if (next) replaceParams({ refresh: next === "15" ? null : next });
          }}
          aria-label="Live refresh interval"
        >
          <ToggleButton value="off">Off</ToggleButton>
          <ToggleButton value="5">5s</ToggleButton>
          <ToggleButton value="15">15s</ToggleButton>
        </ToggleButtonGroup>
        <Button component={Link} href="/data?tab=usage" size="small" variant="outlined">
          LLM usage
        </Button>
      </Stack>

      <Typography variant="subtitle1" sx={{ mb: 1.5 }}>
        Runtime health
      </Typography>

      {dashError || tracesError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {(dashError || tracesError) instanceof Error
            ? (dashError || tracesError)!.message
            : "Could not load observability data"}
        </Alert>
      ) : null}

      {dashLoading ? <SkeletonList rows={3} rowHeight={72} /> : null}

      {dashboard ? (
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" },
            mb: 3,
          }}
        >
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="overline" color="text.secondary">
              Trace volume
            </Typography>
            <Typography variant="h4">{runtime?.trace_volume ?? dashboard.trace_count}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Recent captured runs
            </Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="overline" color="text.secondary">
              Error rate
            </Typography>
            <Typography variant="h4">
              {((runtime?.error_rate ?? 0) * 100).toFixed(1)}%
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {runtime?.error_count ?? 0} failed traces
            </Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="overline" color="text.secondary">
              Latency p95
            </Typography>
            <Typography variant="h4">{formatMs(runtime?.latency_p95_ms)}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Avg {formatMs(runtime?.latency_avg_ms)}
            </Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="overline" color="text.secondary">
              OTEL
            </Typography>
            <Chip
              size="small"
              sx={{ mt: 1 }}
              color={otelOk ? "success" : "default"}
              label={otelOk ? "Connected" : "Not configured"}
            />
            {!otelOk ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Set exporter env vars, then restart the API.{" "}
                <Link href="/settings">Open settings</Link>
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                OpenTelemetry export ready
              </Typography>
            )}
          </Paper>
        </Box>
      ) : null}

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
        <TextField
          size="small"
          label="Search"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          onBlur={() => replaceParams({ q: q.trim() || null })}
          onKeyDown={(event) => {
            if (event.key === "Enter") replaceParams({ q: q.trim() || null });
          }}
          sx={{ minWidth: 200 }}
        />
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="obs-status-label">Status</InputLabel>
          <Select
            labelId="obs-status-label"
            label="Status"
            value={status}
            onChange={(event) => replaceParams({ status: event.target.value || null })}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="ok">ok</MenuItem>
            <MenuItem value="error">error</MenuItem>
            <MenuItem value="running">running</MenuItem>
          </Select>
        </FormControl>
        <TextField
          size="small"
          label="Agent"
          value={agent}
          onChange={(event) => setAgent(event.target.value)}
          onBlur={() => replaceParams({ agent: agent.trim() || null })}
          onKeyDown={(event) => {
            if (event.key === "Enter") replaceParams({ agent: agent.trim() || null });
          }}
          sx={{ minWidth: 160 }}
        />
      </Stack>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Traces
      </Typography>
      {tracesLoading ? <SkeletonTable rows={6} columns={5} /> : null}
      {!tracesLoading && traces.length === 0 ? (
        <Alert severity="info">
          No traces recorded yet. Run an agent workflow to populate this list. Spend metrics stay on{" "}
          <Link href="/data?tab=usage">LLM usage</Link>.
        </Alert>
      ) : null}
      {traces.length > 0 ? (
        <Paper variant="outlined">
          <Table size="small" aria-label="Observability traces">
            <TableHead>
              <TableRow>
                <TableCell>Run</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Agent</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {traces.map((trace) => {
                const id = traceId(trace);
                return (
                  <TableRow key={id || JSON.stringify(trace).slice(0, 40)} hover>
                    <TableCell>
                      <Typography variant="body2" noWrap sx={{ maxWidth: 280 }}>
                        {id || "unknown"}
                      </Typography>
                      {trace.user_request || trace.summary ? (
                        <Typography variant="caption" color="text.secondary" display="block" noWrap>
                          {String(trace.user_request || trace.summary)}
                        </Typography>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={String(trace.status) === "error" ? "error" : "default"}
                        label={String(trace.status || "n/a")}
                      />
                    </TableCell>
                    <TableCell>{String(trace.agent || "-")}</TableCell>
                    <TableCell>{formatMs(trace.duration_ms as number | undefined)}</TableCell>
                    <TableCell align="right">
                      {id ? (
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Button size="small" onClick={() => openTrace(id)}>
                            Spans
                          </Button>
                          <Button
                            component={Link}
                            href={`/agent-runtime?trace_id=${encodeURIComponent(id)}`}
                            size="small"
                          >
                            Full runtime
                          </Button>
                        </Stack>
                      ) : null}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      ) : null}

      <Drawer anchor="right" open={Boolean(selectedId)} onClose={closeTrace}>
        <Box sx={{ width: { xs: "100vw", sm: 420 }, p: 2 }} role="presentation">
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">Span timeline</Typography>
            <Button size="small" onClick={closeTrace}>
              Close
            </Button>
          </Stack>
          {drawerError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {drawerError}
            </Alert>
          ) : null}
          {exportMessage ? (
            <Alert severity="success" sx={{ mb: 2 }}>
              {exportMessage}
            </Alert>
          ) : null}
          {selectedLoading ? <SkeletonList rows={4} rowHeight={40} /> : null}
          {selectedTrace ? (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {traceId(selectedTrace)}
              </Typography>
              <Chip size="small" label={String(selectedTrace.status || selectedTrace.outcome || "n/a")} sx={{ mb: 2 }} />
              <SpanWaterfall spans={selectedTrace.spans || []} />
              <Stack direction="row" spacing={1} sx={{ mt: 3 }}>
                <Button variant="outlined" onClick={() => void handleExport(traceId(selectedTrace))}>
                  Export JSON
                </Button>
                <Button
                  component={Link}
                  href={`/agent-runtime?trace_id=${encodeURIComponent(traceId(selectedTrace))}`}
                  variant="contained"
                >
                  Open full runtime
                </Button>
              </Stack>
            </>
          ) : null}
        </Box>
      </Drawer>
    </Box>
  );
}

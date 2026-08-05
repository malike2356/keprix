"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import { SkeletonList } from "@/components/ui/loading";
import type { EvalTaskResult, EvalTrace } from "@/lib/evals-harness-api";
import { fetchEvalTrace } from "@/lib/evals-harness-api";

type EvalCaseResultDrawerProps = {
  open: boolean;
  task: EvalTaskResult | null;
  suiteName?: string;
  onClose: () => void;
};

function linkForRun(key: string, runId: string): string | null {
  if (key === "playbook") return `/playbooks/${encodeURIComponent(runId)}`;
  if (key === "crew") return `/admin/teams?team=${encodeURIComponent(runId)}`;
  if (key === "browser") return `/browser?session=${encodeURIComponent(runId)}`;
  if (key === "builder") return `/builder/jobs/${encodeURIComponent(runId)}`;
  if (key === "mutation") return `/dashboard/mutation/${encodeURIComponent(runId)}`;
  if (key === "analytics") return `/analytics?session=${encodeURIComponent(runId)}`;
  return null;
}

export default function EvalCaseResultDrawer({ open, task, suiteName, onClose }: EvalCaseResultDrawerProps) {
  const [trace, setTrace] = React.useState<EvalTrace | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open || !task?.trace_id) {
      setTrace(null);
      setError(null);
      return;
    }
    let active = true;
    setLoading(true);
    void fetchEvalTrace(task.trace_id)
      .then((payload) => {
        if (active) setTrace(payload);
      })
      .catch((err) => {
        if (active) {
          setTrace(null);
          setError(err instanceof Error ? err.message : "Could not load trace");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [open, task?.trace_id]);

  const linked = trace?.linked_run_ids ?? {};

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: "100%", sm: 480 }, p: 2 } }}>
      {task ? (
        <Box>
          <Typography variant="h6" gutterBottom>
            Failed case: {task.task_id}
          </Typography>
          {suiteName ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Suite: {suiteName}
            </Typography>
          ) : null}

          <Box sx={{ display: "grid", gap: 1.5, mb: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Expected
              </Typography>
              <Typography variant="body2">{task.expected || trace?.expected || "n/a"}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Actual
              </Typography>
              <Typography variant="body2" component="pre" sx={{ whiteSpace: "pre-wrap", m: 0 }}>
                {task.output || trace?.actual || "n/a"}
              </Typography>
            </Box>
            {task.reason ? (
              <Chip size="small" color="error" label={task.reason} sx={{ alignSelf: "flex-start" }} />
            ) : null}
          </Box>

          {Object.keys(linked).length > 0 ? (
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
              {Object.entries(linked).map(([key, runId]) => {
                const href = linkForRun(key, runId);
                if (!href) return null;
                return (
                  <Button key={key} component={NextLink} href={href} size="small" variant="outlined">
                    Open {key}
                  </Button>
                );
              })}
            </Box>
          ) : null}

          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Trace spans
          </Typography>
          {loading ? <SkeletonList rows={4} rowHeight={40} /> : null}
          {error ? (
            <Typography variant="body2" color="error">
              {error}
            </Typography>
          ) : null}
          {!loading && trace && trace.spans.length > 0 ? (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Span</TableCell>
                  <TableCell>Event</TableCell>
                  <TableCell>Detail</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {trace.spans.map((span, index) => (
                  <TableRow key={`${span.event}-${index}`}>
                    <TableCell>{span.name}</TableCell>
                    <TableCell>
                      <Chip size="small" label={span.event} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" component="pre" sx={{ whiteSpace: "pre-wrap", m: 0 }}>
                        {JSON.stringify(span.payload, null, 2)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
          {!loading && !error && (!trace || trace.spans.length === 0) ? (
            <Typography variant="body2" color="text.secondary">
              No trace spans recorded for this case.
            </Typography>
          ) : null}

          {task.trace_id ? (
            <Box sx={{ mt: 2 }}>
              <Link component={NextLink} href={`/evals?trace=${encodeURIComponent(task.trace_id)}`} variant="body2">
                Permalink trace {task.trace_id.slice(0, 8)}
              </Link>
            </Box>
          ) : null}
        </Box>
      ) : null}
    </Drawer>
  );
}

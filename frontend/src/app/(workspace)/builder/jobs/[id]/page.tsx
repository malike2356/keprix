"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import BuilderTrajectoryPanel from "@/components/builder/BuilderTrajectoryPanel";
import PageHeader from "@/components/ui/PageHeader";
import { fetchBuilderJob, streamBuilderJob } from "@/lib/builder-api";

export default function BuilderJobPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;
  const { data, mutate } = useSWR(jobId ? `builder-job-${jobId}` : null, () => fetchBuilderJob(jobId));
  const [lines, setLines] = React.useState<string[]>([]);
  const [status, setStatus] = React.useState("pending");
  const [diffSummary, setDiffSummary] = React.useState("");

  React.useEffect(() => {
    if (!jobId) return;
    const close = streamBuilderJob(
      jobId,
      (event) => {
        if (event.type === "log" && typeof event.line === "string") {
          const line = event.line;
          setLines((prev) => [...prev, line]);
        }
        if (event.type === "status") {
          if (typeof event.status === "string") setStatus(event.status);
          if (typeof event.diff_summary === "string") setDiffSummary(event.diff_summary);
          void mutate();
        }
      },
      () => {
        void mutate();
      },
    );
    return close;
  }, [jobId, mutate]);

  React.useEffect(() => {
    if (data?.log) {
      setLines(data.log.split("\n").filter(Boolean));
    }
    if (data?.job?.status) {
      setStatus(data.job.status);
    }
    if (data?.job?.diff_summary) {
      setDiffSummary(data.job.diff_summary);
    }
  }, [data]);

  const trajectory = data?.trajectory ?? [];

  return (
    <Box>
      <PageHeader
        title="Build job"
        description={data?.job?.instruction || "Streaming build output"}
      />
      <Box sx={{ display: "flex", gap: 1, mb: 2, alignItems: "center" }}>
        <Chip label={status} />
        <Typography variant="caption" color="text.secondary">
          {jobId}
        </Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1.5 }}>
              Trajectory
            </Typography>
            <BuilderTrajectoryPanel
              steps={trajectory}
              needsTier3Approval={data?.job?.needs_tier3_approval}
              approvalReason={data?.job?.approval_reason}
              mutationId={data?.job?.mutation_id}
            />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              mb: 2,
              bgcolor: "#0f172a",
              color: "#e2e8f0",
              fontFamily: "monospace",
              fontSize: 13,
              minHeight: 320,
              maxHeight: 480,
              overflow: "auto",
              whiteSpace: "pre-wrap",
            }}
          >
            {lines.length ? lines.join("\n") : "Waiting for build log..."}
          </Paper>
          {diffSummary ? (
            <Alert severity="info">
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Git diff summary
              </Typography>
              <Box component="pre" sx={{ m: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
                {diffSummary}
              </Box>
            </Alert>
          ) : null}
        </Grid>
      </Grid>
    </Box>
  );
}

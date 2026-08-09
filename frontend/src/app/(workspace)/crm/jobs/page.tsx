"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { fetchCrmJobs } from "@/lib/crm-api";

export default function CrmJobsPage() {
  const workspaceId = CRM_WORKSPACE;
  const jobs = useSWR(["crm-jobs", workspaceId], () => fetchCrmJobs(workspaceId));
  const discovery = jobs.data?.discovery_jobs ?? [];
  const enrich = jobs.data?.enrichment_jobs ?? [];

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="h6">Jobs</Typography>
        <Button component="a" href="/crm/discover" variant="outlined" size="small">
          New discovery
        </Button>
      </Stack>
      <Typography variant="body2" color="text.secondary">
        Discovery and enrichment job history. Open a job for cancel, Soft Wall materialize, and
        dead-letter retry.
      </Typography>

      {jobs.error ? (
        <Alert severity="error">
          {jobs.error instanceof Error ? jobs.error.message : "Could not load jobs"}
        </Alert>
      ) : null}

      {jobs.isLoading && !jobs.data ? (
        <Typography color="text.secondary">Loading jobs...</Typography>
      ) : discovery.length === 0 && enrich.length === 0 ? (
        <Typography color="text.secondary">No jobs yet. Start from Discover.</Typography>
      ) : (
        <Stack spacing={1.5}>
          {discovery.map((job) => (
            <Card key={job.id} variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Stack direction="row" justifyContent="space-between" spacing={1} flexWrap="wrap" useFlexGap>
                  <Stack spacing={0.5}>
                    <Typography variant="subtitle2">
                      Discovery · {String(job.adapter || "adapter")} · {String(job.status || "")}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Pack {String(job.domain_pack || "generic")}
                      {job.cost_estimate != null ? ` · cost est. ${job.cost_estimate}` : ""}
                      {job.list_id ? ` · list ${job.list_id}` : ""}
                    </Typography>
                    {job.error ? (
                      <Typography variant="body2" color="error">
                        {String(job.error)}
                      </Typography>
                    ) : null}
                  </Stack>
                  <Button
                    component="a"
                    href={`/crm/jobs/${encodeURIComponent(String(job.id))}`}
                    size="small"
                  >
                    Open
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          ))}
          {enrich.map((job) => (
            <Card key={job.id} variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Typography variant="subtitle2">
                  Enrichment · {String(job.status || "")} · {String(job.id)}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}
    </Stack>
  );
}

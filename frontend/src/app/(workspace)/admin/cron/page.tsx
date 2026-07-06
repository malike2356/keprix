"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ScheduleIcon from "@mui/icons-material/Schedule";
import * as React from "react";
import NextLink from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/loading";
import {
  createCronJob,
  deleteCronJob,
  fetchCronJobs,
  fetchCronRuns,
  pauseCronJob,
  resumeCronJob,
  triggerCronJob,
  type CronJob,
  type CronRun,
} from "@/lib/admin-api";

export default function CronAdminPage() {
  const [jobs, setJobs] = React.useState<CronJob[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [runs, setRuns] = React.useState<CronRun[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [schedule, setSchedule] = React.useState("0 9 * * *");
  const [prompt, setPrompt] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setJobs(await fetchCronJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cron jobs");
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  const loadRuns = async (jobId: string) => {
    setSelectedId(jobId);
    try {
      setRuns(await fetchCronRuns(jobId));
    } catch {
      setRuns([]);
    }
  };

  const handleCreate = async () => {
    if (!prompt.trim() || !schedule.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createCronJob({ name: name.trim() || "Scheduled task", schedule, prompt });
      setDialogOpen(false);
      setName("");
      setPrompt("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setSaving(false);
    }
  };

  const handleTrigger = async (jobId: string) => {
    setError(null);
    try {
      await triggerCronJob(jobId);
      await loadRuns(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trigger failed");
    }
  };

  const handleToggle = async (job: CronJob) => {
    setError(null);
    try {
      if (job.enabled === false) {
        await resumeCronJob(job.id);
      } else {
        await pauseCronJob(job.id);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const handleDelete = async (jobId: string) => {
    setError(null);
    try {
      await deleteCronJob(jobId);
      if (selectedId === jobId) {
        setSelectedId(null);
        setRuns([]);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Cron Jobs"
        description="Schedule recurring agent tasks."
        breadcrumbs={[
          { label: "Admin", href: "/admin/cron" },
          { label: "Cron Jobs" },
        ]}
        actions={
          <Button variant="contained" onClick={() => setDialogOpen(true)}>
            Create job
          </Button>
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <SkeletonTable rows={6} columns={5} />
      ) : jobs.length === 0 ? (
        <EmptyState
          title="No scheduled jobs"
          description="Create a cron job with a schedule, prompt, and output channel."
          icon={<ScheduleIcon sx={{ fontSize: 48 }} />}
          actionLabel="Create job"
          onAction={() => setDialogOpen(true)}
        />
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "1fr 320px" },
            gap: 2,
          }}
        >
          <List sx={{ bgcolor: "background.paper", borderRadius: 1, border: 1, borderColor: "divider" }}>
            {jobs.map((job) => (
              <ListItem
                key={job.id}
                divider
                secondaryAction={
                  <Box>
                    <IconButton onClick={() => handleTrigger(job.id)} title="Run now">
                      <PlayArrowIcon />
                    </IconButton>
                    <IconButton onClick={() => handleDelete(job.id)} title="Delete">
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                }
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                      <Typography fontWeight={600}>{job.name || job.id}</Typography>
                      <Chip
                        size="small"
                        label={job.enabled === false ? "Paused" : "Active"}
                        color={job.enabled === false ? "default" : "success"}
                        onClick={() => handleToggle(job)}
                      />
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="caption" display="block">
                        {job.schedule}
                      </Typography>
                      {job.source ? (
                        <Typography variant="caption" display="block">
                          Source:{" "}
                          {job.source_href ? (
                            <NextLink href={job.source_href} style={{ textDecoration: "underline" }}>
                              {job.source}
                            </NextLink>
                          ) : (
                            job.source
                          )}
                        </Typography>
                      ) : null}
                      {job.next_run_at && (
                        <Typography variant="caption" color="text.secondary">
                          Next: {job.next_run_at}
                        </Typography>
                      )}
                    </>
                  }
                  onClick={() => loadRuns(job.id)}
                  sx={{ cursor: "pointer" }}
                />
              </ListItem>
            ))}
          </List>

          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Run history
              </Typography>
              {selectedId ? (
                runs.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No runs recorded for this job.
                  </Typography>
                ) : (
                  <List dense>
                    {runs.map((run) => (
                      <ListItem key={run.id} disablePadding>
                        <ListItemText
                          primary={run.id}
                          secondary={
                            run.is_active
                              ? "Running"
                              : run.ended_at
                                ? `Ended ${new Date(run.ended_at * 1000).toLocaleString()}`
                                : "Completed"
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                )
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Select a job to view run history.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Box>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Create cron job</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <TextField
            label="Schedule (cron)"
            value={schedule}
            onChange={(e) => setSchedule(e.target.value)}
            helperText="Example: 0 9 * * * for daily at 09:00"
          />
          <TextField
            label="Prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            multiline
            minRows={4}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={saving || !prompt.trim()} onClick={handleCreate}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

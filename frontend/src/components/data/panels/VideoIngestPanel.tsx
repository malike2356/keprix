"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { SkeletonTable } from "@/components/ui/loading";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type VideoJob = {
  job_id: string;
  source_type: string;
  source_ref: string;
  mode: string;
  status: string;
  error?: string | null;
  transcript_path?: string | null;
  transcript_text?: string | null;
  manifest_path: string;
  frames: Array<{ path: string; timestamp_sec: number; label?: string }>;
  created_at: string;
  updated_at?: string;
};

const MODE_HELP: Record<string, string> = {
  "caption-only": "Transcript/captions only; skips frame extraction.",
  sparse: "Few key frames across the timeline; fastest visual pass.",
  balanced: "Scene-aware or mid density frames; default for most jobs.",
  dense: "More frames at a fixed interval; best for detailed review, slower.",
};

async function fetchJobs(): Promise<VideoJob[]> {
  const response = await ceApi("/api/ingest/video");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to load video jobs"));
  }
  const payload = (await response.json()) as { jobs: VideoJob[] };
  return payload.jobs;
}

async function fetchJob(jobId: string): Promise<VideoJob> {
  const response = await ceApi(`/api/ingest/video/${encodeURIComponent(jobId)}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to load job"));
  }
  const payload = (await response.json()) as { job: VideoJob };
  return payload.job;
}

function analyzeHref(job: VideoJob): string {
  const prompt = [
    `Analyze video ingest job ${job.job_id}.`,
    `Manifest: ${job.manifest_path}.`,
    job.transcript_path ? `Transcript path: ${job.transcript_path}.` : "",
    `Use vision_analyze on useful frame paths if needed.`,
  ]
    .filter(Boolean)
    .join(" ");
  return `/chat?message=${encodeURIComponent(prompt)}`;
}

function FrameStrip({ jobId, frames }: { jobId: string; frames: VideoJob["frames"] }) {
  const [urls, setUrls] = React.useState<string[]>([]);

  React.useEffect(() => {
    let cancelled = false;
    const created: string[] = [];
    (async () => {
      const next: string[] = [];
      for (let index = 0; index < Math.min(frames.length, 24); index += 1) {
        try {
          const response = await ceApi(`/api/ingest/video/${encodeURIComponent(jobId)}/frames/${index}`);
          if (!response.ok) continue;
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          created.push(url);
          next.push(url);
        } catch {
          // skip missing frames
        }
      }
      if (!cancelled) setUrls(next);
    })();
    return () => {
      cancelled = true;
      created.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [jobId, frames]);

  if (!frames.length) return null;
  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Frame strip
      </Typography>
      <Stack direction="row" spacing={1} sx={{ overflowX: "auto", pb: 1 }}>
        {urls.map((url, index) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={url}
            src={url}
            alt={frames[index]?.label || `Frame ${index}`}
            width={96}
            height={54}
            style={{ objectFit: "cover", borderRadius: 4, border: "1px solid rgba(0,0,0,0.12)" }}
          />
        ))}
        {!urls.length ? (
          <Typography variant="caption" color="text.secondary">
            Loading frame previews...
          </Typography>
        ) : null}
      </Stack>
    </Box>
  );
}

export default function VideoIngestPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("job");

  const [source, setSource] = React.useState("");
  const [mode, setMode] = React.useState("balanced");
  const [copyToVault, setCopyToVault] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const { data, mutate, error, isLoading } = useSWR("video-ingest-jobs", fetchJobs, {
    refreshInterval: (latest) => {
      if (busy) return 2000;
      const jobs = latest || [];
      return jobs.some((job) => ["queued", "running", "pending"].includes(job.status)) ? 3000 : 0;
    },
  });

  const { data: selectedJob, error: selectedError } = useSWR(
    selectedId ? ["video-ingest-job", selectedId] : null,
    () => fetchJob(selectedId as string),
  );

  const openJob = (jobId: string) => {
    const next = new URLSearchParams(searchParams.toString());
    next.set("job", jobId);
    next.set("tab", "video");
    router.replace(`/data?${next.toString()}`);
  };

  const closeJob = () => {
    const next = new URLSearchParams(searchParams.toString());
    next.delete("job");
    next.set("tab", "video");
    router.replace(`/data?${next.toString()}`);
  };

  const startIngest = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const response = await ceApi("/api/ingest/video", {
        method: "POST",
        body: JSON.stringify({ source, mode, copy_to_vault: copyToVault }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(parseApiErrorMessage(payload, "Ingest failed"));
      }
      const payload = (await response.json()) as { job: VideoJob };
      setMessage(
        payload.job.status === "failed"
          ? payload.job.error || "Ingest failed"
          : `Job ${payload.job.job_id} · ${payload.job.status}`,
      );
      await mutate();
      openJob(payload.job.job_id);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setBusy(false);
    }
  };

  const uploadFile = async (file: File) => {
    setBusy(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("mode", mode);
      form.append("copy_to_vault", String(copyToVault));
      const response = await ceApi("/api/ingest/video/upload", {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(parseApiErrorMessage(payload, "Upload failed"));
      }
      const payload = (await response.json()) as { job: VideoJob };
      setSource(payload.job.source_ref || "");
      setMessage(`Uploaded and ingested job ${payload.job.job_id}`);
      await mutate();
      openJob(payload.job.job_id);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const job = selectedJob;

  return (
    <Box sx={{ display: "grid", gap: 2 }}>

      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", md: "1fr 180px auto" },
            alignItems: "center",
          }}
        >
          <TextField
            label="Source URL or local path"
            value={source}
            onChange={(event) => setSource(event.target.value)}
            placeholder="https://youtube.com/watch?v=... or /path/to/demo.mp4"
            helperText={MODE_HELP[mode] || ""}
          />
          <TextField select label="Frame mode" value={mode} onChange={(event) => setMode(event.target.value)}>
            {Object.keys(MODE_HELP).map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
          <FormControlLabel
            control={
              <Switch checked={copyToVault} onChange={(event) => setCopyToVault(event.target.checked)} />
            }
            label="Copy to vault"
          />
        </Box>

        <Box
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            const file = event.dataTransfer.files?.[0];
            if (file) void uploadFile(file);
          }}
          sx={{
            border: "1px dashed",
            borderColor: dragOver ? "primary.main" : "divider",
            borderRadius: 2,
            p: 2,
            textAlign: "center",
            bgcolor: dragOver ? "action.hover" : "transparent",
          }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Drag and drop a video file, or choose one. Uploads save on the API host then ingest.
          </Typography>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*,.mp4,.mov,.mkv,.webm"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void uploadFile(file);
              event.target.value = "";
            }}
          />
          <Stack direction="row" spacing={1} justifyContent="center">
            <Button variant="outlined" disabled={busy} onClick={() => fileInputRef.current?.click()}>
              Choose file
            </Button>
            <Button variant="contained" disabled={!source || busy} onClick={() => void startIngest()}>
              {busy ? "Working..." : "Ingest"}
            </Button>
          </Stack>
        </Box>

        {message ? (
          <Alert severity={/fail|error/i.test(message) ? "error" : "info"}>{message}</Alert>
        ) : null}
      </Paper>

      {error ? (
        <Alert severity="error">{error instanceof Error ? error.message : "Failed to load jobs"}</Alert>
      ) : null}

      {isLoading ? <SkeletonTable rows={5} columns={6} /> : null}

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Table size="small" aria-label="Video ingest jobs">
          <TableHead>
            <TableRow>
              <TableCell>Job</TableCell>
              <TableCell>Source</TableCell>
              <TableCell>Mode</TableCell>
              <TableCell>Frames</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Open</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data ?? []).length === 0 && !isLoading ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    No video jobs yet. Paste a URL/path or upload a file.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : null}
            {(data ?? []).map((row) => (
              <TableRow key={row.job_id} hover selected={selectedId === row.job_id}>
                <TableCell>{row.job_id}</TableCell>
                <TableCell>
                  <Typography variant="body2" noWrap sx={{ maxWidth: 280 }}>
                    {row.source_ref}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {row.source_type}
                  </Typography>
                </TableCell>
                <TableCell>{row.mode}</TableCell>
                <TableCell>{row.frames?.length ?? 0}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    color={
                      row.status === "done" || row.status === "complete"
                        ? "success"
                        : row.status === "failed"
                          ? "error"
                          : "default"
                    }
                    label={row.status}
                  />
                </TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => openJob(row.job_id)}>
                    Details
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Drawer anchor="right" open={Boolean(selectedId)} onClose={closeJob}>
        <Box sx={{ width: { xs: "100vw", sm: 460 }, p: 2 }} role="presentation">
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">Job detail</Typography>
            <Button size="small" onClick={closeJob}>
              Close
            </Button>
          </Stack>
          {selectedError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {selectedError instanceof Error ? selectedError.message : "Failed to load job"}
            </Alert>
          ) : null}
          {job ? (
            <Stack spacing={2}>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  Status
                </Typography>
                <Chip size="small" label={job.status} sx={{ ml: 1 }} />
                {job.error ? (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {job.error}
                  </Alert>
                ) : null}
              </Box>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  Created
                </Typography>
                <Typography variant="body2">{job.created_at}</Typography>
              </Box>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  Frames
                </Typography>
                <Typography variant="body2">{job.frames?.length ?? 0}</Typography>
              </Box>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  Manifest
                </Typography>
                <Typography variant="body2" sx={{ wordBreak: "break-all" }}>
                  {job.manifest_path}
                </Typography>
              </Box>

              {(job.frames?.length ?? 0) > 0 ? <FrameStrip jobId={job.job_id} frames={job.frames} /> : null}

              {(job.transcript_text || job.transcript_path) && (
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Transcript / captions
                  </Typography>
                  {job.transcript_path ? (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                      {job.transcript_path}
                    </Typography>
                  ) : null}
                  <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 220, overflow: "auto" }}>
                    <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                      {job.transcript_text || "(Transcript file saved; text not inlined.)"}
                    </Typography>
                  </Paper>
                </Box>
              )}

              <Stack direction="row" spacing={1}>
                <Button component="a" href={analyzeHref(job)} variant="contained">
                  Open in chat
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                Retry and cancel are hidden until the API supports them.
              </Typography>
            </Stack>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Loading job...
            </Typography>
          )}
        </Box>
      </Drawer>
    </Box>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import LinearProgress from "@mui/material/LinearProgress";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import StatusPill from "@/components/ui/StatusPill";
import ResearchWorkspaceShell from "@/components/research/ResearchWorkspaceShell";
import NotebookDepthPanel from "./NotebookDepthPanel";
import {
  downloadResearchExport,
  deleteResearchJob,
  fetchResearchPresets,
  fetchResearchReport,
  fetchResearchJobs,
  startResearch,
  watchResearchJob,
  type ResearchDepth,
  type ResearchJob,
  type ResearchStreamEvent,
} from "@/lib/research-api";
import { normalizeStatusKey, type StatusKey } from "@/theme/tokens/status";

const DEPTH_LABELS: Record<ResearchDepth, string> = {
  quick: "Quick",
  standard: "Standard",
  deep: "Deep",
};

const DEFAULT_MODEL_VALUE = "default";

type ResearchTab = "deep" | "projects";

function researchStatusKey(status: string | null): StatusKey {
  if (!status) {
    return "draft";
  }
  if (status === "error") {
    return "failed";
  }
  if (status === "cancelled") {
    return "archived";
  }
  return normalizeStatusKey(status);
}

function formatRunTime(value?: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString();
}

export default function ResearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobFromUrl = searchParams.get("job");

  const [tab, setTab] = React.useState<ResearchTab>("deep");
  const [query, setQuery] = React.useState("");
  const [depth, setDepth] = React.useState<ResearchDepth>("standard");
  const [model, setModel] = React.useState(DEFAULT_MODEL_VALUE);
  const [presets, setPresets] = React.useState<Record<string, { model: string; note: string }>>({});
  const [activeJobId, setActiveJobId] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);
  const [events, setEvents] = React.useState<ResearchStreamEvent[]>([]);
  const [report, setReport] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [reconnected, setReconnected] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [history, setHistory] = React.useState<ResearchJob[]>([]);
  const [exportMessage, setExportMessage] = React.useState<string | null>(null);
  const [exportBusy, setExportBusy] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);

  const streamAbortRef = React.useRef<AbortController | null>(null);
  const watchingJobRef = React.useRef<string | null>(null);

  const refreshHistory = React.useCallback(async () => {
    const jobs = await fetchResearchJobs().catch(() => []);
    setHistory(jobs);
    return jobs;
  }, []);

  const setJobInUrl = React.useCallback(
    (jobId: string) => {
      if (searchParams.get("job") === jobId) {
        return;
      }
      router.replace(`/research?job=${encodeURIComponent(jobId)}`, { scroll: false });
    },
    [router, searchParams],
  );

  const watchJob = React.useCallback(
    async (jobId: string, options?: { reconnect?: boolean }) => {
      streamAbortRef.current?.abort();
      const controller = new AbortController();
      streamAbortRef.current = controller;
      watchingJobRef.current = jobId;

      setActiveJobId(jobId);
      setJobInUrl(jobId);
      setLoading(true);
      setError(null);
      setEvents([]);
      setReport(null);
      setReconnected(Boolean(options?.reconnect));

      try {
        const job = await watchResearchJob(
          jobId,
          (event) => {
            setEvents((prev) => [...prev, event]);
            if (event.status) {
              setStatus(event.status);
            }
            if (event.type === "complete") {
              setStatus(event.status || "complete");
            }
          },
          controller.signal,
        );

        setQuery(job.query);
        setDepth(job.depth as ResearchDepth);
        setStatus(job.status);

        try {
          const markdown = await fetchResearchReport(jobId);
          setReport(markdown);
        } catch {
          if (job.error_message) {
            setReport(`# Research failed\n\n${job.error_message}\n`);
          }
        }

        await refreshHistory();
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setError(err instanceof Error ? err.message : "Research failed");
        setStatus((current) => current || "failed");
      } finally {
        if (watchingJobRef.current === jobId) {
          setLoading(false);
        }
      }
    },
    [refreshHistory, setJobInUrl],
  );

  const watchJobRef = React.useRef(watchJob);
  watchJobRef.current = watchJob;

  React.useEffect(() => {
    fetchResearchPresets()
      .then(setPresets)
      .catch(() => setPresets({}));
    void refreshHistory();
  }, [refreshHistory]);

  React.useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      const jobs = await refreshHistory();
      if (cancelled) {
        return;
      }

      const targetId = jobFromUrl || jobs.find((job) => job.status === "running")?.job_id;
      if (!targetId) {
        return;
      }
      if (watchingJobRef.current === targetId) {
        return;
      }

      await watchJobRef.current(targetId, {
        reconnect: !jobFromUrl && jobs.some((job) => job.job_id === targetId && job.status === "running"),
      });
    };

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [jobFromUrl, refreshHistory]);

  React.useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  React.useEffect(() => {
    if (status !== "running") {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshHistory();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [refreshHistory, status]);

  const progressLabel = React.useMemo(() => {
    const last = events[events.length - 1];
    if (!last) {
      return "Starting research pipeline";
    }
    if (last.type === "sub_question_start") {
      return `Planning ${last.sub_questions?.length || 0} sub-questions`;
    }
    if (last.type === "source_fetched") {
      return `Searching: ${last.question || "sub-question"}`;
    }
    if (last.type === "source_read") {
      return `Reading: ${last.title || last.url || "source"}`;
    }
    if (last.type === "synthesis_chunk") {
      return "Synthesizing report";
    }
    if (last.type === "complete") {
      return "Research complete";
    }
    return "Research in progress";
  }, [events]);

  const handleStart = async () => {
    if (!query.trim() || loading) {
      return;
    }
    setLoading(true);
    setError(null);
    setEvents([]);
    setReport(null);
    setReconnected(false);
    setStatus("running");
    try {
      const started = await startResearch(
        query.trim(),
        depth,
        model === DEFAULT_MODEL_VALUE ? undefined : model,
      );
      await watchJob(started.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research failed");
      setStatus("failed");
      setLoading(false);
    }
  };

  const statusKey = researchStatusKey(status);
  const showProgress = loading || status === "running";
  const activeJob = history.find((job) => job.job_id === activeJobId);
  const canExport = Boolean(report && activeJobId && !showProgress);

  const handleExport = async (format: "pdf" | "html" | "markdown" | "docx") => {
    if (!activeJobId) {
      return;
    }
    setExportBusy(true);
    setExportMessage(null);
    try {
      const result = await downloadResearchExport(activeJobId, format);
      if (result.fallback) {
        setExportMessage(result.fallback);
      }
    } catch (err) {
      setExportMessage(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExportBusy(false);
    }
  };

  const handleCopyMarkdown = async () => {
    if (!report) {
      return;
    }
    try {
      await navigator.clipboard.writeText(report);
      setExportMessage("Markdown copied to clipboard.");
    } catch {
      setExportMessage("Could not copy Markdown to clipboard.");
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!window.confirm("Delete this research run? This cannot be undone.")) {
      return;
    }
    setDeleteError(null);
    try {
      await deleteResearchJob(jobId);
      if (activeJobId === jobId) {
        streamAbortRef.current?.abort();
        watchingJobRef.current = null;
        setActiveJobId(null);
        setReport(null);
        setStatus(null);
        setEvents([]);
        setError(null);
        setReconnected(false);
        if (searchParams.get("job")) {
          router.replace("/research", { scroll: false });
        }
      }
      await refreshHistory();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Could not delete research run");
    }
  };

  const presetModels = React.useMemo(
    () => Object.entries(presets).map(([tier, preset]) => ({ tier, ...preset })),
    [presets],
  );

  const deepResearchPanel = (
    <>
      <NotebookDepthPanel />

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <TextField
            label="Research query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            fullWidth
            multiline
            minRows={2}
            placeholder="What should Keprix investigate?"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                void handleStart();
              }
            }}
          />
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.5}
            alignItems={{ xs: "stretch", sm: "flex-end" }}
            sx={{ mt: 2 }}
          >
            <FormControl size="small" sx={{ minWidth: { sm: 140 } }}>
              <InputLabel id="depth-label">Depth</InputLabel>
              <Select
                labelId="depth-label"
                label="Depth"
                value={depth}
                onChange={(e) => setDepth(e.target.value as ResearchDepth)}
              >
                {(Object.keys(DEPTH_LABELS) as ResearchDepth[]).map((key) => (
                  <MenuItem key={key} value={key}>
                    {DEPTH_LABELS[key]}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: { sm: 200 }, flex: { sm: 1 } }}>
              <InputLabel id="model-label" shrink>
                Model
              </InputLabel>
              <Select
                labelId="model-label"
                label="Model"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                renderValue={(selected) => {
                  if (selected === DEFAULT_MODEL_VALUE) {
                    return "Default";
                  }
                  const preset = presetModels.find((entry) => entry.model === selected);
                  return preset ? `${preset.tier}: ${preset.model}` : selected;
                }}
              >
                <MenuItem value={DEFAULT_MODEL_VALUE}>Default</MenuItem>
                {presetModels.map((preset) => (
                  <MenuItem key={preset.tier} value={preset.model} title={preset.note}>
                    {preset.tier}: {preset.model}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="contained"
              disabled={!query.trim() || loading}
              onClick={() => void handleStart()}
              sx={{ whiteSpace: "nowrap" }}
            >
              {loading ? "Running..." : "Start research"}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {reconnected && showProgress ? (
        <Alert severity="info" sx={{ mb: 2 }} onClose={() => setReconnected(false)}>
          Reconnected to your in-progress research. You can leave this page; the run continues on the server.
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      {deleteError ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setDeleteError(null)}>
          {deleteError}
        </Alert>
      ) : null}

      {showProgress ? (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1.5 }}>
              <Typography variant="body2" sx={{ flex: 1 }}>
                {progressLabel}
              </Typography>
              {status ? <StatusPill status={statusKey} /> : null}
            </Stack>
            <LinearProgress
              variant={activeJob?.progress_pct ? "determinate" : "indeterminate"}
              value={activeJob?.progress_pct || 0}
            />
            {activeJobId ? (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                Run {activeJobId}
              </Typography>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {report ? (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1} sx={{ mb: 1 }}>
              <Typography variant="subtitle1">Report</Typography>
              {status ? <StatusPill status={statusKey} /> : null}
            </Stack>
            {canExport ? (
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
                <Button
                  variant="contained"
                  size="small"
                  disabled={exportBusy}
                  onClick={() => void handleExport("pdf")}
                >
                  Download PDF
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  disabled={exportBusy}
                  onClick={() => void handleExport("docx")}
                >
                  Download Word
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  disabled={exportBusy}
                  onClick={() => void handleExport("html")}
                >
                  Download HTML
                </Button>
                <Button variant="text" size="small" disabled={exportBusy} onClick={() => void handleCopyMarkdown()}>
                  Copy Markdown
                </Button>
              </Stack>
            ) : null}
            {exportMessage ? (
              <Alert severity="info" sx={{ mb: 2 }} onClose={() => setExportMessage(null)}>
                {exportMessage}
              </Alert>
            ) : null}
            <Box
              sx={{
                "& h1, & h2, & h3": { mt: 2 },
                "& p, & li": { lineHeight: 1.7 },
                "& pre": { overflow: "auto", p: 1, bgcolor: "action.hover", borderRadius: 1 },
              }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
            </Box>
          </CardContent>
        </Card>
      ) : null}

      {history.length > 0 ? (
        <Box>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            Research runs
          </Typography>
          <List dense disablePadding>
            {history.map((job) => {
              const selected = job.job_id === activeJobId;
              return (
                <ListItemButton
                  key={job.job_id}
                  selected={selected}
                  onClick={() => void watchJob(job.job_id)}
                  sx={{ borderRadius: 1, mb: 0.5 }}
                >
                  <ListItemText
                    primary={job.query}
                    secondary={`${DEPTH_LABELS[job.depth as ResearchDepth] || job.depth} · ${formatRunTime(job.started_at)}`}
                    primaryTypographyProps={{ noWrap: true }}
                  />
                  <StatusPill status={researchStatusKey(job.status)} />
                  <IconButton
                    size="small"
                    aria-label="Delete research run"
                    sx={{ ml: 0.5, opacity: 0.7, ".MuiListItemButton-root:hover &": { opacity: 1 } }}
                    onClick={(event) => {
                      event.stopPropagation();
                      void handleDeleteJob(job.job_id);
                    }}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </ListItemButton>
              );
            })}
          </List>
        </Box>
      ) : null}
    </>
  );

  return (
    <Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "flex-start", sm: "center" }}
        justifyContent="space-between"
        spacing={1}
        sx={{ mb: 2 }}
      >
        <Typography variant="h5" component="h1">
          Research
        </Typography>
        <Tabs
          value={tab}
          onChange={(_e, value: ResearchTab) => setTab(value)}
          sx={{ minHeight: 40, "& .MuiTab-root": { minHeight: 40, py: 0.5, px: 2 } }}
        >
          <Tab value="deep" label="Deep research" />
          <Tab value="projects" label="Projects" />
        </Tabs>
      </Stack>

      <ResearchWorkspaceShell tab={tab} deepResearchPanel={deepResearchPanel} />
    </Box>
  );
}

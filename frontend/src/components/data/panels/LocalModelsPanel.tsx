"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import MemoryIcon from "@mui/icons-material/Memory";
import Link from "next/link";
import * as React from "react";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonStatGrid } from "@/components/ui/loading";
import { setStoredModel } from "@/hooks/useChat";
import {
  listPlaybookModels,
  listServing,
  pingServingHealth,
  scanHardware,
  serveModel,
  startModelDownload,
  stopModel,
  watchModelDownload,
  type HardwareScan,
  type PlaybookModel,
} from "@/lib/playbook-api";

const SCAN_CACHE_KEY = "keprix-local-models-scan-cache-v1";

type ScanCache = {
  hardware: HardwareScan;
  models: PlaybookModel[];
  serving: Array<{ model_id: string; backend: string; port: number }>;
  savedAt: number;
};

type PullJob = {
  modelId: string;
  progress: number;
  status: "running" | "complete" | "failed";
  log?: string;
};

function fitColor(score: number): "success" | "warning" | "error" | "default" {
  if (score >= 0.9) return "success";
  if (score >= 0.6) return "warning";
  if (score >= 0.3) return "default";
  return "error";
}

function failureHints(hardware: HardwareScan | null, model: PlaybookModel): string[] {
  const hints: string[] = [];
  if (!hardware) {
    hints.push("Run a hardware scan first.");
    return hints;
  }
  if (model.vram_gb > 0 && hardware.gpu_vram_gb < model.vram_gb) {
    hints.push(
      `VRAM short: model wants ~${model.vram_gb} GB, host has ${hardware.gpu_vram_gb || 0} GB. Pick a smaller quant or CPU-friendly model.`,
    );
  }
  if (hardware.free_disk_gb < Math.max(4, model.size_b * 0.6)) {
    hints.push(
      `Disk short: free space is ${hardware.free_disk_gb} GB. Free disk before pulling ~${model.size_b}B weights.`,
    );
  }
  if (model.fit_score < 0.3) {
    hints.push("Fit score is low for this host; prefer a smaller model from the list.");
  }
  if (!hints.length && model.fit_score < 0.6) {
    hints.push("Tight fit: watch memory pressure after serve.");
  }
  return hints;
}

function readScanCache(): ScanCache | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(SCAN_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ScanCache;
    if (!parsed?.hardware || !Array.isArray(parsed.models)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeScanCache(cache: ScanCache): void {
  localStorage.setItem(SCAN_CACHE_KEY, JSON.stringify(cache));
}

export default function LocalModelsPanel() {
  const [hardware, setHardware] = React.useState<HardwareScan | null>(null);
  const [models, setModels] = React.useState<PlaybookModel[]>([]);
  const [serving, setServing] = React.useState<Array<{ model_id: string; backend: string; port: number }>>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [actionModelId, setActionModelId] = React.useState<string | null>(null);
  const [pullJobs, setPullJobs] = React.useState<Record<string, PullJob>>({});
  const [healthByPort, setHealthByPort] = React.useState<Record<number, { ok: boolean; message: string }>>({});
  const [copiedUrl, setCopiedUrl] = React.useState<string | null>(null);
  const [useChatNote, setUseChatNote] = React.useState<string | null>(null);

  const refreshServing = React.useCallback(async () => {
    const active = await listServing();
    setServing(active);
    const ports = Array.from(new Set(active.map((entry) => entry.port || 11434)));
    const healthEntries = await Promise.all(
      ports.map(async (port) => {
        const probe = await pingServingHealth(port);
        return [
          port,
          {
            ok: probe.ok,
            message: probe.ok
              ? `Healthy · ${probe.base_url}`
              : `${probe.error || "Daemon down"}. ${probe.fix || ""}`.trim(),
          },
        ] as const;
      }),
    );
    setHealthByPort(Object.fromEntries(healthEntries));
  }, []);

  const loadScan = React.useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!opts?.silent) setLoading(true);
      setError(null);
      try {
        const [scan, catalog, active] = await Promise.all([
          scanHardware(),
          listPlaybookModels(),
          listServing(),
        ]);
        setHardware(scan);
        setModels(catalog.models);
        setServing(active);
        writeScanCache({
          hardware: scan,
          models: catalog.models,
          serving: active,
          savedAt: Date.now(),
        });
        await refreshServing();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Scan failed");
      } finally {
        if (!opts?.silent) setLoading(false);
      }
    },
    [refreshServing],
  );

  React.useEffect(() => {
    const cached = readScanCache();
    if (cached) {
      setHardware(cached.hardware);
      setModels(cached.models);
      setServing(cached.serving || []);
      void refreshServing();
    }
    void loadScan({ silent: Boolean(cached) });
  }, [loadScan, refreshServing]);

  const handleDownload = async (modelId: string) => {
    setActionModelId(modelId);
    setError(null);
    setPullJobs((prev) => ({
      ...prev,
      [modelId]: { modelId, progress: 0, status: "running" },
    }));
    try {
      await startModelDownload(modelId);
      const finalEvent = await watchModelDownload(modelId, (event) => {
        setPullJobs((prev) => ({
          ...prev,
          [modelId]: {
            modelId,
            progress: event.progress_pct ?? prev[modelId]?.progress ?? 0,
            status: event.status === "failed" ? "failed" : event.status === "complete" ? "complete" : "running",
            log: event.log?.slice(-1)[0],
          },
        }));
      });
      const failed = finalEvent.status === "failed";
      setPullJobs((prev) => ({
        ...prev,
        [modelId]: {
          modelId,
          progress: finalEvent.progress_pct ?? (failed ? prev[modelId]?.progress || 0 : 100),
          status: failed ? "failed" : "complete",
        },
      }));
      if (failed) {
        setError(
          `Pull failed for ${modelId}. Check that the Ollama daemon is running (\`ollama serve\`) and disk/VRAM are available.`,
        );
      }
    } catch (err) {
      setPullJobs((prev) => ({
        ...prev,
        [modelId]: { modelId, progress: prev[modelId]?.progress || 0, status: "failed" },
      }));
      const message = err instanceof Error ? err.message : "Download failed";
      if (/ollama|daemon|not found|PATH/i.test(message)) {
        setError(`${message}. Fix: install Ollama and run \`ollama serve\`, then retry Pull.`);
      } else {
        setError(message);
      }
    } finally {
      setActionModelId(null);
    }
  };

  const handleServe = async (modelId: string) => {
    setActionModelId(modelId);
    setError(null);
    try {
      await serveModel(modelId);
      await refreshServing();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Serve failed");
    } finally {
      setActionModelId(null);
    }
  };

  const handleStop = async (modelId: string) => {
    setActionModelId(modelId);
    setError(null);
    try {
      await stopModel(modelId);
      await refreshServing();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stop failed");
    } finally {
      setActionModelId(null);
    }
  };

  const handleUseInChat = (modelId: string) => {
    setStoredModel(modelId);
    setUseChatNote(`Selected ${modelId} for chat. Open chat to confirm the model picker.`);
  };

  const copyBaseUrl = async (port: number) => {
    const url = `http://127.0.0.1:${port}/v1`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedUrl(url);
    } catch {
      setError(`Could not copy ${url}`);
    }
  };

  const pullJobList = Object.values(pullJobs);

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
        <Button variant="contained" onClick={() => void loadScan()} disabled={loading}>
          {loading ? "Scanning..." : "Refresh scan"}
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        Looking for Playbooks (automations)?{" "}
        <Link href="/playbooks">Open Playbooks</Link>
      </Alert>

      {useChatNote ? (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          action={
            <Button component={Link} href="/chat" color="inherit" size="small">
              Open chat
            </Button>
          }
          onClose={() => setUseChatNote(null)}
        >
          {useChatNote}
        </Alert>
      ) : null}

      {copiedUrl ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setCopiedUrl(null)}>
          Copied {copiedUrl}
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Serving inventory
          </Typography>
          {serving.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No models registered for serving yet. Pull a model, then click Serve.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {serving.map((entry) => {
                const port = entry.port || 11434;
                const health = healthByPort[port];
                const baseUrl = `http://127.0.0.1:${port}/v1`;
                return (
                  <Stack
                    key={entry.model_id}
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1}
                    alignItems={{ sm: "center" }}
                    justifyContent="space-between"
                  >
                    <Box>
                      <Chip
                        size="small"
                        color={health?.ok ? "success" : "warning"}
                        label={`${entry.model_id} · ${entry.backend}:${port}`}
                        sx={{ mr: 1 }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {health?.message || "Checking health..."}
                      </Typography>
                      <Typography variant="body2" sx={{ fontFamily: "monospace", mt: 0.5 }}>
                        {baseUrl}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="Copy base URL">
                        <IconButton
                          size="small"
                          aria-label={`Copy base URL for ${entry.model_id}`}
                          onClick={() => void copyBaseUrl(port)}
                        >
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Button size="small" onClick={() => handleUseInChat(entry.model_id)}>
                        Use in chat
                      </Button>
                      <Button
                        size="small"
                        color="warning"
                        disabled={actionModelId === entry.model_id}
                        onClick={() => void handleStop(entry.model_id)}
                      >
                        Stop
                      </Button>
                    </Stack>
                  </Stack>
                );
              })}
            </Stack>
          )}
        </CardContent>
      </Card>

      {pullJobList.length > 0 ? (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Pull jobs
            </Typography>
            <Stack spacing={1.5}>
              {pullJobList.map((job) => (
                <Box key={job.modelId}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2">{job.modelId}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {job.status} · {job.progress}%
                    </Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={job.progress}
                    color={job.status === "failed" ? "error" : "primary"}
                    sx={{ mt: 0.5 }}
                  />
                  {job.log ? (
                    <Typography variant="caption" color="text.secondary" display="block">
                      {job.log}
                    </Typography>
                  ) : null}
                </Box>
              ))}
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Cancel is not available for in-flight pulls yet; stop the Ollama process on the host if needed.
            </Typography>
          </CardContent>
        </Card>
      ) : null}

      {loading && !hardware ? (
        <Box sx={{ mb: 3 }}>
          <SkeletonStatGrid count={4} />
        </Box>
      ) : null}

      {hardware ? (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
            gap: 2,
            mb: 3,
          }}
        >
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                RAM
              </Typography>
              <Typography variant="h6">{hardware.total_ram_gb} GB</Typography>
              <Typography variant="caption" color="text.secondary">
                Available {hardware.available_ram_gb} GB
              </Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                GPU VRAM
              </Typography>
              <Typography variant="h6">
                {hardware.has_gpu ? `${hardware.gpu_vram_gb} GB` : "CPU only"}
              </Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                CPU
              </Typography>
              <Typography variant="h6">{hardware.cpu_cores} cores</Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Free disk
              </Typography>
              <Typography variant="h6">{hardware.free_disk_gb} GB</Typography>
            </CardContent>
          </Card>
        </Box>
      ) : null}

      {hardware && models.length > 0 ? (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recommended models
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Model</TableCell>
                  <TableCell>Family</TableCell>
                  <TableCell align="right">VRAM req.</TableCell>
                  <TableCell align="right">Fit</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {models.map((model) => {
                  const hints = failureHints(hardware, model);
                  return (
                    <TableRow key={model.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {model.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {model.quant}
                        </Typography>
                        {hints.length ? (
                          <Typography variant="caption" color="warning.main" display="block">
                            {hints[0]}
                          </Typography>
                        ) : null}
                      </TableCell>
                      <TableCell>{model.family}</TableCell>
                      <TableCell align="right">{model.vram_gb} GB</TableCell>
                      <TableCell align="right">
                        <Chip size="small" color={fitColor(model.fit_score)} label={model.fit_score.toFixed(2)} />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          sx={{ mr: 1 }}
                          disabled={actionModelId === model.id || pullJobs[model.id]?.status === "running"}
                          onClick={() => void handleDownload(model.id)}
                        >
                          Pull
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          sx={{ mr: 1 }}
                          disabled={actionModelId === model.id}
                          onClick={() => void handleServe(model.id)}
                        >
                          Serve
                        </Button>
                        <Button size="small" onClick={() => handleUseInChat(model.id)}>
                          Use in chat
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}

      {!hardware && !loading ? (
        <EmptyState
          title="No hardware scan yet"
          description="Auto-scan runs on first visit. Refresh if hardware changed."
          icon={<MemoryIcon sx={{ fontSize: 48 }} />}
          actionLabel="Scan hardware"
          onAction={() => void loadScan()}
        />
      ) : null}
    </Box>
  );
}

"use client";

import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  fetchDeploymentStatus,
  fetchPipelineEvaluations,
  fetchPipelineRuns,
  queryPipeline,
  type EvaluationReport,
  type PipelineRun,
} from "@/lib/rag-pipeline-api";

type Props = {
  pipelineId: string;
};

const STEP_ORDER = ["converter", "cleaner", "chunker", "embedder", "writer", "retriever", "ranker", "generator"];

function stepLabel(name: string): string {
  const map: Record<string, string> = {
    converter: "ingest",
    cleaner: "clean",
    chunker: "chunk",
    embedder: "embed",
    writer: "write",
    retriever: "retrieve",
    ranker: "rank",
    generator: "generate",
  };
  return map[name] || name;
}

export default function PipelineRunViewer({ pipelineId }: Props) {
  const [question, setQuestion] = React.useState("What does Building 3 maintenance cover?");
  const [run, setRun] = React.useState<PipelineRun | null>(null);
  const [runs, setRuns] = React.useState<PipelineRun[]>([]);
  const [evaluations, setEvaluations] = React.useState<EvaluationReport[]>([]);
  const [deploymentReady, setDeploymentReady] = React.useState<boolean | null>(null);
  const [deployPlain, setDeployPlain] = React.useState<string>("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [filter, setFilter] = React.useState("");
  const [citationPreview, setCitationPreview] = React.useState<Record<string, unknown> | null>(null);

  const refresh = React.useCallback(async () => {
    const [runPayload, evalPayload, deployPayload] = await Promise.all([
      fetchPipelineRuns(pipelineId, filter || undefined),
      fetchPipelineEvaluations(pipelineId),
      fetchDeploymentStatus(pipelineId),
    ]);
    setRuns(runPayload.runs || []);
    setEvaluations(evalPayload.evaluations || []);
    setDeploymentReady(deployPayload.ready);
    setDeployPlain(deployPayload.plain || "");
  }, [pipelineId, filter]);

  React.useEffect(() => {
    refresh().catch(() => null);
  }, [refresh]);

  const onQuery = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await queryPipeline({ pipeline_id: pipelineId, question });
      setRun(result);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setBusy(false);
    }
  };

  const replay = (item: PipelineRun) => {
    const metaQ = String((item.metadata as { question?: string } | undefined)?.question || "");
    if (metaQ) setQuestion(metaQ);
    setRun(item);
  };

  const latency = (run?.trace || []).reduce<Record<string, number>>((acc, step) => {
    const name = String(step.component || "");
    const ms = Number((run as { latency_ms?: Record<string, number> })?.latency_ms?.[name] ?? step.latency_ms ?? 0);
    if (name) acc[name] = ms;
    return acc;
  }, {});

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
          <Typography variant="h6">Run panel</Typography>
          {deploymentReady === null ? null : (
            <Chip
              size="small"
              label={deploymentReady ? "deployment ready" : "deployment gated"}
              color={deploymentReady ? "success" : "warning"}
            />
          )}
        </Box>
        {deployPlain ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {deployPlain}
          </Typography>
        ) : null}

        <Box sx={{ display: "grid", gap: 2, mt: 2 }}>
          <TextField
            label="Question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            size="small"
            multiline
            minRows={2}
          />
          <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={() => void onQuery()} disabled={busy}>
            Run query
          </Button>
        </Box>

        {error ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        ) : null}

        {run ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Answer
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
              {run.answer || "No answer returned."}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              route: {run.route || "unknown"} | confidence: {run.confidence ?? 0}
            </Typography>

            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              Step timeline
            </Typography>
            {(run.trace || []).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No trace steps on this run.
              </Typography>
            ) : (
              <Stack spacing={0.75} sx={{ mt: 1 }}>
                {(run.trace || [])
                  .slice()
                  .sort((a, b) => {
                    const ai = STEP_ORDER.indexOf(String(a.component || ""));
                    const bi = STEP_ORDER.indexOf(String(b.component || ""));
                    return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
                  })
                  .map((step, index) => {
                    const name = String(step.component || `step-${index}`);
                    const err = step.error ? String(step.error) : "";
                    return (
                      <Box key={`${name}-${index}`} sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                        <Chip size="small" color={err ? "error" : "default"} label={stepLabel(name)} />
                        <Typography variant="caption" color="text.secondary">
                          {latency[name] ? `${latency[name].toFixed(0)} ms` : "ok"}
                          {err ? ` · ${err}` : ""}
                        </Typography>
                      </Box>
                    );
                  })}
              </Stack>
            )}

            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              Citations
            </Typography>
            {(run.citations || []).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No citations.
              </Typography>
            ) : (
              (run.citations || []).map((cite, index) => (
                <Button
                  key={`${cite.source}-${index}`}
                  size="small"
                  sx={{ display: "block", textAlign: "left", justifyContent: "flex-start", mb: 0.5 }}
                  onClick={() => setCitationPreview(cite)}
                >
                  [{index + 1}] {String(cite.source || "source")}: {String(cite.snippet || "").slice(0, 120)}
                </Button>
              ))
            )}
          </Box>
        ) : null}

        {evaluations.length ? (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2">Latest evaluation</Typography>
            <Typography variant="caption" sx={{ display: "block" }}>
              precision {evaluations[0].retrieval_precision.toFixed(2)} | faithfulness{" "}
              {evaluations[0].citation_faithfulness.toFixed(2)} | hallucination risk{" "}
              {evaluations[0].hallucination_risk.toFixed(2)} | latency {evaluations[0].latency_ms.toFixed(0)}ms
            </Typography>
          </Box>
        ) : null}

        <Box sx={{ mt: 3 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle2" sx={{ flex: 1 }}>
              History
            </Typography>
            <TextField
              size="small"
              label="Filter runs"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              sx={{ width: 200 }}
            />
          </Stack>
          {runs.length === 0 ? (
            <Alert severity="info">No runs yet for this pipeline. Ingest a source, then run a query.</Alert>
          ) : (
            runs
              .slice()
              .reverse()
              .slice(0, 20)
              .map((item) => (
                <Stack
                  key={item.run_id}
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  sx={{ py: 0.5, borderBottom: 1, borderColor: "divider" }}
                >
                  <Typography variant="caption" sx={{ flex: 1 }}>
                    {item.run_id.slice(0, 8)} · {item.route || "n/a"} · {(item.answer || "").slice(0, 48)}
                  </Typography>
                  <Button size="small" onClick={() => replay(item)}>
                    Replay
                  </Button>
                </Stack>
              ))
          )}
        </Box>
      </CardContent>

      <Dialog open={Boolean(citationPreview)} onClose={() => setCitationPreview(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Citation preview</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(citationPreview, null, 2)}
          </Typography>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

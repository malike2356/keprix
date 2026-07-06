"use client";

import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
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

export default function PipelineRunViewer({ pipelineId }: Props) {
  const [question, setQuestion] = React.useState("What does Building 3 maintenance cover?");
  const [run, setRun] = React.useState<PipelineRun | null>(null);
  const [runs, setRuns] = React.useState<PipelineRun[]>([]);
  const [evaluations, setEvaluations] = React.useState<EvaluationReport[]>([]);
  const [deploymentReady, setDeploymentReady] = React.useState<boolean | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    const [runPayload, evalPayload, deployPayload] = await Promise.all([
      fetchPipelineRuns(pipelineId),
      fetchPipelineEvaluations(pipelineId),
      fetchDeploymentStatus(pipelineId),
    ]);
    setRuns(runPayload.runs || []);
    setEvaluations(evalPayload.evaluations || []);
    setDeploymentReady(deployPayload.ready);
  }, [pipelineId]);

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

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
          <Typography variant="h6">Pipeline runs</Typography>
          {deploymentReady === null ? null : (
            <Chip
              size="small"
              label={deploymentReady ? "deployment ready" : "deployment gated"}
              color={deploymentReady ? "success" : "warning"}
            />
          )}
        </Box>
        <Box sx={{ display: "grid", gap: 2, mt: 2 }}>
          <TextField
            label="Question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            size="small"
            multiline
            minRows={2}
          />
          <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={onQuery} disabled={busy}>
            Run query pipeline
          </Button>
        </Box>
        {error ? (
          <Typography color="error" variant="body2" sx={{ mt: 2 }}>
            {error}
          </Typography>
        ) : null}
        {run ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
              {run.answer}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              route: {run.route || "unknown"} | confidence: {run.confidence ?? 0}
            </Typography>
            {(run.citations || []).map((cite, index) => (
              <Typography key={`${cite.source}-${index}`} variant="caption" sx={{ display: "block" }}>
                [{index + 1}] {String(cite.source)}: {String(cite.snippet)}
              </Typography>
            ))}
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              playbook run: {run.playbook_run_id || "n/a"} | evaluation: {run.evaluation_id || "n/a"}
            </Typography>
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
        {runs.length ? (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2">Recent runs</Typography>
            {runs.slice(-5).reverse().map((item) => (
              <Typography key={item.run_id} variant="caption" sx={{ display: "block" }}>
                {item.run_id.slice(0, 8)} route={item.route || "n/a"}
              </Typography>
            ))}
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}

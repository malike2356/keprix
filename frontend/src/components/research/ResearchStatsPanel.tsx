"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import * as React from "react";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  downloadResearchDatasetExport,
  fetchPsppStatus,
  generatePsppAnalysis,
  previewResearchDataset,
  runPsppAnalysis,
  type PsppRunResult,
  type PsppStatus,
} from "@/lib/research-workspace-api";

type AnalysisPreset = "summary" | "compare" | "correlations";

type Props = {
  datasetId: string | null;
  onComplete?: () => void;
};

function buildProcedures(preset: AnalysisPreset, columns: string[]): Array<Record<string, unknown>> {
  const variables = columns.filter(Boolean).slice(0, 6);
  if (!variables.length) {
    return [{ type: "frequencies", variables: ["value"] }];
  }
  if (preset === "compare" && variables.length >= 2) {
    return [{ type: "crosstabs", row: variables[0], column: variables[1] }];
  }
  if (preset === "correlations" && variables.length >= 2) {
    return [{ type: "correlations", variables }];
  }
  return [{ type: "descriptives", variables }];
}

export default function ResearchStatsPanel({ datasetId, onComplete }: Props) {
  const [status, setStatus] = React.useState<PsppStatus | null>(null);
  const [columns, setColumns] = React.useState<string[]>([]);
  const [preset, setPreset] = React.useState<AnalysisPreset>("summary");
  const [busy, setBusy] = React.useState(false);
  const [jamoviBusy, setJamoviBusy] = React.useState(false);
  const [result, setResult] = React.useState<PsppRunResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetchPsppStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  React.useEffect(() => {
    if (!datasetId) {
      setColumns([]);
      setResult(null);
      return;
    }
    previewResearchDataset(datasetId)
      .then((payload) => setColumns(payload.columns || []))
      .catch(() => setColumns([]));
  }, [datasetId]);

  const runAnalysis = async () => {
    if (!datasetId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    setResult(null);
    try {
      const generated = await generatePsppAnalysis(datasetId, buildProcedures(preset, columns));
      const run = await runPsppAnalysis(generated.run_id);
      setResult(run);
      if (run.status === "complete") {
        setMessage("Analysis finished. Review the output below.");
      } else if (run.status === "syntax_only") {
        setMessage("PSPP syntax was saved. Install PSPP on this server to run analyses automatically.");
      } else {
        setMessage("Analysis completed with warnings. Check the output.");
      }
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  };

  const downloadJamovi = async () => {
    if (!datasetId) return;
    setJamoviBusy(true);
    setError(null);
    try {
      await downloadResearchDatasetExport(datasetId, "jamovi");
      setMessage("jamovi package downloaded. Open the zip file in jamovi on your computer.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "jamovi download failed");
    } finally {
      setJamoviBusy(false);
    }
  };

  if (!datasetId) {
    return (
      <Typography variant="body2" color="text.secondary">
        Import a dataset to run PSPP or prepare a jamovi package.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Typography variant="subtitle2">Statistical analysis</Typography>
      <Typography variant="caption" color="text.secondary">
        Free tools: PSPP runs on the server when installed. jamovi runs on your computer after download.
      </Typography>

      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <Typography variant="body2">PSPP:</Typography>
        {status?.installed ? (
          <Chip size="small" color="success" label={`Ready${status.version ? ` (${status.version})` : ""}`} />
        ) : (
          <Chip size="small" color="warning" label="Not installed on server" />
        )}
      </Box>

      <FormControl size="small" fullWidth>
        <InputLabel id="analysis-preset-label">Analysis type</InputLabel>
        <Select
          labelId="analysis-preset-label"
          label="Analysis type"
          value={preset}
          onChange={(event) => setPreset(event.target.value as AnalysisPreset)}
        >
          <MenuItem value="summary">Summary tables (descriptives)</MenuItem>
          <MenuItem value="compare">Compare groups (crosstabs)</MenuItem>
          <MenuItem value="correlations">Correlations</MenuItem>
        </Select>
      </FormControl>

      <Button variant="contained" size="small" onClick={runAnalysis} disabled={busy}>
        {busy ? "Running analysis..." : "Run analysis with PSPP"}
      </Button>

      {!status?.installed && status?.setup_instructions ? (
        <Alert severity="info">
          PSPP is not on this server yet. Keprix will still save syntax you can run locally. Ask your admin to
          install PSPP, or download the syntax file from Advanced export below.
        </Alert>
      ) : null}

      <Divider />

      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        jamovi (desktop app)
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Download a zip with your data and labels, then open it in jamovi.
      </Typography>
      <Button variant="outlined" size="small" onClick={downloadJamovi} disabled={jamoviBusy}>
        {jamoviBusy ? "Preparing download..." : "Download for jamovi"}
      </Button>

      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      {result ? (
        <Box sx={{ bgcolor: "action.hover", borderRadius: 1, p: 1.5 }}>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
            Output ({result.status})
          </Typography>
          {result.parsed_tables && result.parsed_tables.length > 0 ? (
            <StructuredDataView value={result.parsed_tables} />
          ) : (
            <Box component="pre" sx={{ fontSize: 12, m: 0, overflow: "auto", maxHeight: 200, whiteSpace: "pre-wrap" }}>
              {result.stdout || result.stderr || status?.setup_instructions || "No text output."}
            </Box>
          )}
        </Box>
      ) : null}
    </Box>
  );
}

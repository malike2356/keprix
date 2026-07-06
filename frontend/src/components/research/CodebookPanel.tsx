"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  downloadResearchDatasetExport,
  exportResearchDataset,
  fetchResearchDataset,
  updateResearchCodebook,
} from "@/lib/research-workspace-api";

type Props = {
  datasetId: string | null;
};

export default function CodebookPanel({ datasetId }: Props) {
  const [codebookJson, setCodebookJson] = React.useState("");
  const [advancedOpen, setAdvancedOpen] = React.useState(false);
  const [exportFormat, setExportFormat] = React.useState("jamovi");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!datasetId) {
      setCodebookJson("");
      return;
    }
    fetchResearchDataset(datasetId)
      .then((payload) => setCodebookJson(JSON.stringify(payload.codebook, null, 2)))
      .catch(() => setCodebookJson(""));
  }, [datasetId]);

  const saveCodebook = async () => {
    if (!datasetId) return;
    setError(null);
    try {
      const codebook = JSON.parse(codebookJson);
      await updateResearchCodebook(datasetId, codebook);
      setMessage("Variable labels saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const exportDataset = async () => {
    if (!datasetId) return;
    setBusy(true);
    setError(null);
    try {
      if (exportFormat === "jamovi") {
        await downloadResearchDatasetExport(datasetId, "jamovi");
        setMessage("jamovi package downloaded.");
      } else if (exportFormat === "pspp") {
        await downloadResearchDatasetExport(datasetId, "pspp");
        setMessage("PSPP syntax file downloaded.");
      } else if (exportFormat === "csv") {
        await downloadResearchDatasetExport(datasetId, "csv");
        setMessage("Clean CSV downloaded.");
      } else {
        const result = await exportResearchDataset(datasetId, exportFormat);
        setMessage(`Exported as ${result.format}.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  if (!datasetId) {
    return (
      <Typography variant="body2" color="text.secondary">
        Import a dataset to edit variable labels or download exports.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Export and labels</Typography>
      <FormControl size="small" sx={{ minWidth: 180 }}>
        <InputLabel id="export-format-label">Download as</InputLabel>
        <Select
          labelId="export-format-label"
          label="Download as"
          value={exportFormat}
          onChange={(e) => setExportFormat(String(e.target.value))}
        >
          <MenuItem value="jamovi">jamovi package (zip)</MenuItem>
          <MenuItem value="pspp">PSPP syntax (.sps)</MenuItem>
          <MenuItem value="csv">Clean CSV</MenuItem>
          <MenuItem value="r">R script</MenuItem>
          <MenuItem value="python">Python notebook cell</MenuItem>
          <MenuItem value="json-schema">JSON schema</MenuItem>
        </Select>
      </FormControl>
      <Button size="small" variant="outlined" onClick={exportDataset} disabled={busy}>
        {busy ? "Preparing..." : "Download"}
      </Button>
      <Link
        component="button"
        variant="body2"
        color="text.secondary"
        onClick={() => setAdvancedOpen((open) => !open)}
        sx={{ cursor: "pointer", textAlign: "left" }}
      >
        {advancedOpen ? "Hide advanced codebook" : "Advanced: edit variable labels (JSON)"}
      </Link>
      <Collapse in={advancedOpen}>
        <TextField
          size="small"
          label="Codebook JSON"
          value={codebookJson}
          onChange={(e) => setCodebookJson(e.target.value)}
          multiline
          minRows={6}
          fullWidth
        />
        <Button size="small" variant="text" onClick={saveCodebook} sx={{ mt: 1 }}>
          Save labels
        </Button>
      </Collapse>
      {message ? (
        <Typography variant="body2" color="text.secondary">
          {message}
        </Typography>
      ) : null}
      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : null}
    </Box>
  );
}

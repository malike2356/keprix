"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import * as React from "react";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { importResearchDataset, previewResearchDataset } from "@/lib/research-workspace-api";

type Props = {
  projectId: string | null;
  onImported?: (datasetId: string) => void;
};

export default function DatasetManager({ projectId, onImported }: Props) {
  const [name, setName] = React.useState("Survey dataset");
  const [file, setFile] = React.useState<File | null>(null);
  const [datasetId, setDatasetId] = React.useState<string | null>(null);
  const [preview, setPreview] = React.useState<{ columns: string[]; rows: Array<Record<string, unknown>> } | null>(
    null,
  );
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [dragActive, setDragActive] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const importDataset = async (selectedFile?: File) => {
    const upload = selectedFile || file;
    if (!projectId || !upload) return;
    setBusy(true);
    setError(null);
    try {
      const result = await importResearchDataset(projectId, name, upload);
      setDatasetId(result.dataset_id);
      onImported?.(result.dataset_id);
      const sample = await previewResearchDataset(result.dataset_id);
      setPreview(sample);
      setMessage(
        `Imported ${upload.name} with ${result.codebook.variables.length} variables. You can run analysis below.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
      setDragActive(false);
    }
  };

  if (!projectId) {
    return (
      <Typography variant="body2" color="text.secondary">
        Select a project to import datasets.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Your dataset</Typography>
      <Typography variant="caption" color="text.secondary">
        SPSS (.sav), Excel, CSV, TSV, JSON, or Parquet. Your original file is kept; Keprix builds a codebook
        automatically.
      </Typography>
      <TextField size="small" label="Dataset name" value={name} onChange={(e) => setName(e.target.value)} />
      <input
        ref={fileInputRef}
        hidden
        type="file"
        accept=".csv,.tsv,.json,.parquet,.xlsx,.sav"
        onChange={(event) => {
          const selected = event.target.files?.[0] || null;
          setFile(selected);
          event.target.value = "";
        }}
      />
      <Box
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          const dropped = event.dataTransfer.files?.[0];
          if (dropped) {
            setFile(dropped);
            void importDataset(dropped);
          }
        }}
        onClick={() => fileInputRef.current?.click()}
        sx={{
          p: 2,
          border: "1px dashed",
          borderColor: dragActive ? "primary.main" : "divider",
          borderRadius: 1,
          bgcolor: dragActive ? "action.hover" : "background.default",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 1.5,
        }}
      >
        <UploadFileOutlinedIcon color="action" fontSize="small" />
        <Box>
          <Typography variant="body2">
            {busy ? "Importing..." : file ? file.name : "Drop a file here or click to choose"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Includes SPSS .sav files from IBM SPSS
          </Typography>
        </Box>
      </Box>
      <Button size="small" variant="contained" onClick={() => void importDataset()} disabled={!file || busy}>
        {busy ? "Importing..." : "Import dataset"}
      </Button>
      {datasetId ? (
        <Typography variant="caption" color="text.secondary">
          Active dataset: {datasetId}
        </Typography>
      ) : null}
      {preview ? (
        <StructuredDataView
          value={{ columns: preview.columns, sample_rows: preview.rows.slice(0, 3) }}
        />
      ) : null}
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

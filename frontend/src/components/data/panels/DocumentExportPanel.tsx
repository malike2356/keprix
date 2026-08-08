"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import {
  createDocumentExport,
  exportDownloadHref,
  isRestrictedClassification,
} from "@/lib/document-export-api";

export default function DocumentExportPanel() {
  const [title, setTitle] = React.useState("Export");
  const [markdown, setMarkdown] = React.useState("# Heading\n\nBody text.");
  const [classification, setClassification] = React.useState("INTERNAL");
  const [format, setFormat] = React.useState<"html" | "pdf">("html");
  const [includeCover, setIncludeCover] = React.useState(true);
  const [includeSignatory, setIncludeSignatory] = React.useState(false);
  const [signatoryName, setSignatoryName] = React.useState("");
  const [signatoryTitle, setSignatoryTitle] = React.useState("");
  const [preparedBy, setPreparedBy] = React.useState("");
  const [documentType, setDocumentType] = React.useState("Report");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = React.useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  async function doExport() {
    setBusy(true);
    setError(null);
    setMessage(null);
    setDownloadUrl(null);
    try {
      const result = await createDocumentExport({
        title: title.trim() || "Export",
        markdown,
        content: markdown,
        input_type: "markdown",
        classification,
        format,
        include_cover: includeCover,
        include_signatory: includeSignatory,
        document_type: documentType,
        prepared_by: preparedBy,
        signatory_data: includeSignatory
          ? { name: signatoryName, title: signatoryTitle }
          : undefined,
      });
      setDownloadUrl(exportDownloadHref(result.file_url));
      setMessage(`Export ready: ${result.filename} (${result.size_bytes ?? "?"} bytes)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
      setConfirmOpen(false);
    }
  }

  function onSubmit() {
    if (isRestrictedClassification(classification)) {
      setConfirmOpen(true);
      return;
    }
    void doExport();
  }

  return (
    <Box>
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
          {downloadUrl ? (
            <Button component={NextLink} href={downloadUrl} size="small" sx={{ ml: 1 }}>
              Download
            </Button>
          ) : null}
        </Alert>
      ) : null}

      <Alert severity="info" sx={{ mb: 2 }}>
        Signed/cover exports use `/api/export`. Simple document downloads remain on{" "}
        <Button component={NextLink} href="/documents" size="small">
          Documents
        </Button>
        .
      </Alert>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={1.5}>
          <TextField size="small" label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <TextField
            size="small"
            label="Document type"
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
          />
          <TextField
            size="small"
            label="Prepared by"
            value={preparedBy}
            onChange={(e) => setPreparedBy(e.target.value)}
          />
          <TextField
            select
            size="small"
            label="Classification"
            value={classification}
            onChange={(e) => setClassification(e.target.value)}
          >
            {["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET"].map((c) => (
              <MenuItem key={c} value={c}>
                {c}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label="Format"
            value={format}
            onChange={(e) => setFormat(e.target.value as "html" | "pdf")}
          >
            <MenuItem value="html">HTML</MenuItem>
            <MenuItem value="pdf">PDF</MenuItem>
          </TextField>
          <FormControlLabel
            control={<Checkbox checked={includeCover} onChange={(e) => setIncludeCover(e.target.checked)} />}
            label="Include cover page"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={includeSignatory}
                onChange={(e) => setIncludeSignatory(e.target.checked)}
              />
            }
            label="Include signatory block"
          />
          {includeSignatory ? (
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
              <TextField
                size="small"
                label="Signatory name"
                value={signatoryName}
                onChange={(e) => setSignatoryName(e.target.value)}
              />
              <TextField
                size="small"
                label="Signatory title"
                value={signatoryTitle}
                onChange={(e) => setSignatoryTitle(e.target.value)}
              />
            </Stack>
          ) : null}
          <TextField
            label="Markdown content"
            multiline
            minRows={8}
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            helperText="Do not paste secrets or credentials into export payloads."
          />
          <Button variant="contained" disabled={busy || !markdown.trim()} onClick={onSubmit}>
            Create export
          </Button>
        </Stack>
      </Paper>

      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
        Restricted classifications require Soft Wall confirmation before render.
      </Typography>

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>Restricted classification export?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Soft Wall confirm: export with classification {classification}. Confirm only if the
            destination and audience are approved.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button color="warning" variant="contained" disabled={busy} onClick={() => void doExport()}>
            Confirm export
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

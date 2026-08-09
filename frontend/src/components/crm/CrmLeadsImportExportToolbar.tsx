"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  exportCrmLeadsWorkbook,
  ingestCrmLeadsFile,
  previewCrmLeadsIngest,
} from "@/lib/crm-api";
import { CRM_WORKSPACE } from "@/components/crm/types";

type CrmLeadsImportExportToolbarProps = {
  workspaceId?: string;
  filter?: Record<string, unknown>;
  onImported: () => void;
};

export default function CrmLeadsImportExportToolbar({
  workspaceId = CRM_WORKSPACE,
  filter,
  onImported,
}: CrmLeadsImportExportToolbarProps) {
  const [open, setOpen] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [preview, setPreview] = React.useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = React.useState(false);
  const fileRef = React.useRef<HTMLInputElement | null>(null);

  const onFile = async (file: File) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const text = await file.text();
      const lines = text.split(/\r?\n/).filter(Boolean);
      if (lines.length >= 2 && (file.name.endsWith(".csv") || file.name.endsWith(".tsv"))) {
        const delim = file.name.endsWith(".tsv") ? "\t" : ",";
        const headers = lines[0].split(delim).map((h) => h.trim());
        const rows = lines.slice(1, 21).map((line) => {
          const cells = line.split(delim);
          const row: Record<string, unknown> = {};
          headers.forEach((h, i) => {
            row[h] = cells[i] ?? "";
          });
          return row;
        });
        const mapped = await previewCrmLeadsIngest({ rows, limit: 10 }, workspaceId);
        setPreview(mapped as unknown as Record<string, unknown>);
      } else {
        setPreview({ note: "Binary sheet selected; import will use server readers.", filename: file.name });
      }
      const result = await ingestCrmLeadsFile(file, workspaceId);
      setMessage(
        `Imported: created ${String(result.created ?? 0)}, updated ${String(result.updated ?? 0)}, duplicates ${String(result.duplicate ?? 0)}.`,
      );
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  const onExportFilter = async (format: "xlsx" | "csv") => {
    setBusy(true);
    setError(null);
    try {
      const blob = await exportCrmLeadsWorkbook({ filter: filter || {}, format }, workspaceId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `keprix-leads-filter.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage(`Exported current filter as ${format.toUpperCase()}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
        <Button size="small" variant="outlined" onClick={() => setOpen(true)} aria-label="Open import wizard">
          Import
        </Button>
        <Button size="small" variant="outlined" disabled={busy} onClick={() => void onExportFilter("xlsx")}>
          Export filter XLSX
        </Button>
        <Button size="small" variant="outlined" disabled={busy} onClick={() => void onExportFilter("csv")}>
          Export filter CSV
        </Button>
        <Link href="/crm/enrich" underline="hover" variant="body2" sx={{ alignSelf: "center" }}>
          Open enrich sheet flow
        </Link>
      </Stack>
      {message ? <Alert severity="success" sx={{ mb: 1 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert> : null}

      <Drawer anchor="right" open={open} onClose={() => setOpen(false)} PaperProps={{ sx: { width: { xs: "100%", sm: 440 } } }}>
        <Stack spacing={1.5} sx={{ p: 2 }}>
          <Typography variant="h6">Import leads</Typography>
          <Typography variant="body2" color="text.secondary">
            Upload CSV/XLSX/ODS. Mapping preview uses ingest-preview; apply calls real ingest APIs. You can also continue in{" "}
            <Link href="/crm/enrich">/crm/enrich</Link>.
          </Typography>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.tsv,.xlsx,.xls,.ods,text/csv"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void onFile(file);
            }}
          />
          <Button variant="contained" disabled={busy} onClick={() => fileRef.current?.click()}>
            Choose file
          </Button>
          {preview ? (
            <Stack spacing={0.5}>
              <Typography variant="subtitle2">Mapping preview</Typography>
              <Typography component="pre" variant="caption" sx={{ whiteSpace: "pre-wrap" }}>
                {JSON.stringify(preview, null, 2).slice(0, 4000)}
              </Typography>
            </Stack>
          ) : null}
        </Stack>
      </Drawer>
    </>
  );
}

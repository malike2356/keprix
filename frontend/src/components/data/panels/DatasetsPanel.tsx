"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Drawer from "@mui/material/Drawer";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonTable } from "@/components/ui/loading";
import {
  deleteDataDataset,
  exportDataDataset,
  fetchDataCatalog,
  fetchDataImportFormats,
  fetchDataPlanesStatus,
  fetchDatasetVersions,
  importDataDataset,
  queryDataDataset,
  type DataPlaneDataset,
} from "@/lib/data-plane-api";

const ROW_PAGE = 50;

export default function DatasetsPanel() {
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [file, setFile] = React.useState<File | null>(null);
  const [importName, setImportName] = React.useState("");
  const [selected, setSelected] = React.useState<DataPlaneDataset | null>(null);
  const [sql, setSql] = React.useState("SELECT * FROM data LIMIT 50");
  const [queryRows, setQueryRows] = React.useState<Record<string, unknown>[]>([]);
  const [queryCols, setQueryCols] = React.useState<string[]>([]);
  const [page, setPage] = React.useState(0);
  const [deleteTarget, setDeleteTarget] = React.useState<DataPlaneDataset | null>(null);
  const [versionsOpen, setVersionsOpen] = React.useState(false);

  const catalog = useSWR("data-catalog", fetchDataCatalog);
  const planes = useSWR("data-planes-status", fetchDataPlanesStatus);
  const formats = useSWR("data-import-formats", fetchDataImportFormats);
  const versions = useSWR(
    selected && versionsOpen ? `data-versions-${selected.id}` : null,
    () => fetchDatasetVersions(selected!.id),
  );

  const datasets = catalog.data?.datasets ?? [];

  async function onImport() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await importDataDataset(file, importName.trim() || undefined);
      setFile(null);
      setImportName("");
      setMessage("Dataset imported.");
      await catalog.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  async function onQuery() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const result = await queryDataDataset(selected.id, sql);
      setQueryCols(result.columns || []);
      setQueryRows(result.rows || []);
      setPage(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const result = await exportDataDataset(selected.id, "csv");
      setMessage(`Export written: ${result.path} (${result.bytes ?? "?"} bytes)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmDelete() {
    if (!deleteTarget) return;
    setBusy(true);
    setError(null);
    try {
      await deleteDataDataset(deleteTarget.id);
      setMessage(`Deleted ${deleteTarget.name}.`);
      if (selected?.id === deleteTarget.id) {
        setSelected(null);
        setQueryRows([]);
        setQueryCols([]);
      }
      setDeleteTarget(null);
      await catalog.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  const pageRows = queryRows.slice(page * ROW_PAGE, page * ROW_PAGE + ROW_PAGE);

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
        </Alert>
      ) : null}

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Plane status
        </Typography>
        {planes.error ? (
          <Alert severity="warning">Could not load plane integrity status.</Alert>
        ) : (
          <StructuredDataView value={planes.data || {}} emptyLabel="No plane status" />
        )}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Import dataset
        </Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems="flex-start">
          <Button variant="outlined" component="label" disabled={busy}>
            Choose file
            <input
              hidden
              type="file"
              accept={(formats.data?.formats || ["csv", "tsv", "parquet", "xlsx"]).map((f) => `.${f}`).join(",")}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </Button>
          <TextField
            size="small"
            label="Name (optional)"
            value={importName}
            onChange={(e) => setImportName(e.target.value)}
          />
          <Button variant="contained" disabled={busy || !file} onClick={() => void onImport()}>
            Upload
          </Button>
        </Stack>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          {file ? `Selected: ${file.name}` : "Supported: CSV, TSV, Parquet, Excel, SPSS when available."}
        </Typography>
      </Paper>

      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Catalog
      </Typography>
      {catalog.isLoading ? (
        <SkeletonTable rows={4} />
      ) : datasets.length === 0 ? (
        <EmptyState title="No datasets" description="Import a CSV or Parquet file to start querying." />
      ) : (
        <Table size="small" sx={{ mb: 2 }}>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Format</TableCell>
              <TableCell>Rows</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {datasets.map((row) => (
              <TableRow
                key={row.id}
                selected={selected?.id === row.id}
                hover
                onClick={() => setSelected(row)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell>{row.name}</TableCell>
                <TableCell>{row.format}</TableCell>
                <TableCell>{row.row_count ?? "-"}</TableCell>
                <TableCell>{row.created_at || "-"}</TableCell>
                <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button
                      size="small"
                      onClick={() => {
                        setSelected(row);
                        setVersionsOpen(true);
                      }}
                    >
                      Versions
                    </Button>
                    <Button size="small" color="error" onClick={() => setDeleteTarget(row)}>
                      Delete
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {selected ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1" sx={{ flex: 1 }}>
              Query: {selected.name}
            </Typography>
            <Button size="small" disabled={busy} onClick={() => void onExport()}>
              Export CSV copy
            </Button>
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onQuery()}>
              Run query
            </Button>
          </Stack>
          <TextField
            fullWidth
            multiline
            minRows={3}
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            helperText="Read-only SELECT queries against the selected dataset."
          />
          {queryCols.length ? (
            <Box sx={{ mt: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    {queryCols.map((col) => (
                      <TableCell key={col}>{col}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pageRows.map((row, idx) => (
                    <TableRow key={idx}>
                      {queryCols.map((col) => (
                        <TableCell key={col}>{String(row[col] ?? "")}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Button size="small" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                  Prev
                </Button>
                <Typography variant="body2" sx={{ alignSelf: "center" }}>
                  Page {page + 1} / {Math.max(1, Math.ceil(queryRows.length / ROW_PAGE))}
                </Typography>
                <Button
                  size="small"
                  disabled={(page + 1) * ROW_PAGE >= queryRows.length}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </Stack>
            </Box>
          ) : null}
        </Paper>
      ) : null}

      <Drawer anchor="right" open={versionsOpen} onClose={() => setVersionsOpen(false)}>
        <Box sx={{ width: 360, p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Versions
          </Typography>
          {versions.isLoading ? (
            <Typography variant="body2">Loading...</Typography>
          ) : (versions.data?.items || []).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No versions recorded.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {(versions.data?.items || []).map((v) => (
                <Paper key={v.version_id} variant="outlined" sx={{ p: 1.5 }}>
                  <Typography variant="body2">v{v.version_number}</Typography>
                  <Typography variant="caption" display="block">
                    {v.created_at}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    rows: {v.row_count ?? "-"}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          )}
        </Box>
      </Drawer>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete dataset?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Soft Wall confirm: permanently delete {deleteTarget?.name}. This cannot be undone from
            the GUI.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button color="error" variant="contained" disabled={busy} onClick={() => void onConfirmDelete()}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

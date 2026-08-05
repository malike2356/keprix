"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import RefreshIcon from "@mui/icons-material/Refresh";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import * as React from "react";
import useSWR from "swr";
import {
  addDiskFolder,
  createDocumentIndex,
  deleteDiskFolder,
  deleteDocumentIndex,
  fetchDiskFolders,
  fetchDocumentConnectors,
  fetchDocumentIndexes,
  inspectDocumentIndex,
  refreshDocumentIndex,
  syncDiskFolder,
  uploadToDocumentIndex,
} from "@/lib/documents-api";

export default function IndexManagerPanel() {
  const { data, mutate, error } = useSWR("document-indexes", () => fetchDocumentIndexes());
  const { data: connectors } = useSWR("document-connectors", () => fetchDocumentConnectors());
  const {
    data: diskData,
    mutate: mutateDisk,
    error: diskError,
  } = useSWR("document-disk-folders", () => fetchDiskFolders());
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [name, setName] = React.useState("Workspace corpus");
  const [folderPath, setFolderPath] = React.useState("/data/keprix/docs");
  const [folderName, setFolderName] = React.useState("Disk docs");
  const [alsoImport, setAlsoImport] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [localError, setLocalError] = React.useState<string | null>(null);

  const indexes = data?.indexes ?? [];
  const folders = diskData?.folders ?? [];
  const diskRoots = diskData?.disk_roots || (connectors as { disk_roots?: string[] } | undefined)?.disk_roots || [];
  const activeId = selectedId || indexes[0]?.index_id || null;
  const { data: coverage, mutate: refreshCoverage } = useSWR(
    activeId ? ["document-index-coverage", activeId] : null,
    () => inspectDocumentIndex(activeId as string),
  );

  async function onCreate() {
    setBusy(true);
    setLocalError(null);
    try {
      const created = await createDocumentIndex(name.trim() || "Workspace corpus");
      setSelectedId(created.index_id);
      setMessage(`Created index ${created.name}`);
      await mutate();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRefresh() {
    if (!activeId) return;
    setBusy(true);
    try {
      await refreshDocumentIndex(activeId);
      await mutate();
      await refreshCoverage();
      setMessage("Index refreshed");
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!activeId) return;
    if (!window.confirm("Delete this index?")) return;
    setBusy(true);
    try {
      await deleteDocumentIndex(activeId);
      setSelectedId(null);
      await mutate();
      setMessage("Index deleted");
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file?: File | null) {
    if (!file) return;
    let indexId = activeId;
    setBusy(true);
    setLocalError(null);
    try {
      if (!indexId) {
        const created = await createDocumentIndex(name.trim() || "Workspace corpus");
        indexId = created.index_id;
        setSelectedId(indexId);
      }
      await uploadToDocumentIndex(indexId, file);
      await mutate();
      await refreshCoverage();
      setMessage(`Uploaded ${file.name}`);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onAddDiskFolder() {
    if (!folderPath.trim()) {
      setLocalError("Folder path is required");
      return;
    }
    setBusy(true);
    setLocalError(null);
    try {
      const created = await addDiskFolder({
        path: folderPath.trim(),
        name: folderName.trim() || undefined,
        index_id: activeId || undefined,
        also_import_workspace: alsoImport,
      });
      setSelectedId(created.index_id);
      const sync = created.initial_sync || {};
      setMessage(
        `Linked folder. Indexed ${Number(sync.indexed || 0)} files` +
          (alsoImport ? `, imported ${Number(sync.imported_workspace || 0)} to library` : ""),
      );
      await mutate();
      await mutateDisk();
      await refreshCoverage();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Failed to link disk folder");
    } finally {
      setBusy(false);
    }
  }

  async function onSyncFolder(folderId: string) {
    setBusy(true);
    try {
      const result = await syncDiskFolder(folderId);
      setMessage(`Synced folder: ${Number(result.indexed || 0)} files indexed`);
      await mutate();
      await mutateDisk();
      await refreshCoverage();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Folder sync failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteFolder(folderId: string) {
    if (!window.confirm("Remove this disk folder link?")) return;
    setBusy(true);
    try {
      await deleteDiskFolder(folderId);
      await mutateDisk();
      setMessage("Disk folder link removed");
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1, gap: 1, flexWrap: "wrap" }}>
          <Typography variant="h6">Index manager</Typography>
          <Stack direction="row" spacing={1}>
            <Button size="small" startIcon={<RefreshIcon />} onClick={() => void onRefresh()} disabled={busy || !activeId}>
              Refresh index
            </Button>
            <Button size="small" color="error" startIcon={<DeleteIcon />} onClick={() => void onDelete()} disabled={busy || !activeId}>
              Delete
            </Button>
          </Stack>
        </Box>

        {message ? (
          <Alert severity="success" sx={{ mb: 1 }} onClose={() => setMessage(null)}>
            {message}
          </Alert>
        ) : null}
        {localError || error || diskError ? (
          <Alert severity="error" sx={{ mb: 1 }} onClose={() => setLocalError(null)}>
            {localError ||
              (error instanceof Error ? error.message : null) ||
              (diskError instanceof Error ? diskError.message : "Failed to load indexes")}
          </Alert>
        ) : null}

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Connectors: {(connectors?.connectors || []).join(", ") || "file, text, url, disk"}
        </Typography>
        {diskRoots.length ? (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            Allowed disk roots: {diskRoots.slice(0, 4).join(" · ")}
          </Typography>
        ) : null}

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
          <TextField size="small" label="New index name" value={name} onChange={(e) => setName(e.target.value)} fullWidth />
          <Button variant="contained" onClick={() => void onCreate()} disabled={busy}>
            Create index
          </Button>
          <Button component="label" variant="outlined" startIcon={<UploadFileIcon />} disabled={busy}>
            Upload file
            <input hidden type="file" onChange={(e) => void onUpload(e.target.files?.[0])} />
          </Button>
        </Stack>

        <Box sx={{ mb: 2, p: 1.5, border: 1, borderColor: "divider", borderRadius: 1, display: "grid", gap: 1 }}>
          <Typography variant="subtitle2">Link disk folder</Typography>
          <TextField
            size="small"
            label="Folder path on server"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            placeholder="/data/keprix/docs"
          />
          <TextField size="small" label="Display name" value={folderName} onChange={(e) => setFolderName(e.target.value)} />
          <FormControlLabel
            control={<Switch checked={alsoImport} onChange={(e) => setAlsoImport(e.target.checked)} />}
            label="Also import into Documents library"
          />
          <Button variant="outlined" onClick={() => void onAddDiskFolder()} disabled={busy}>
            Link and sync folder
          </Button>
          {folders.map((folder) => (
            <Box
              key={folder.id}
              sx={{ display: "flex", justifyContent: "space-between", gap: 1, flexWrap: "wrap", alignItems: "center" }}
            >
              <Box>
                <Typography sx={{ fontWeight: 600 }}>{folder.name}</Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  {folder.path} · {folder.file_count} files
                  {folder.last_sync_at ? ` · last sync ${new Date(folder.last_sync_at).toLocaleString()}` : ""}
                </Typography>
                {folder.last_sync_error ? (
                  <Typography variant="caption" color="error" display="block">
                    {folder.last_sync_error}
                  </Typography>
                ) : null}
              </Box>
              <Stack direction="row" spacing={1}>
                <Button size="small" onClick={() => void onSyncFolder(folder.id)} disabled={busy}>
                  Sync
                </Button>
                <Button size="small" color="error" onClick={() => void onDeleteFolder(folder.id)} disabled={busy}>
                  Remove
                </Button>
              </Stack>
            </Box>
          ))}
        </Box>

        <Stack spacing={1} sx={{ mb: 2 }}>
          {indexes.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No indexes yet. Create one, upload files, or link a disk folder.
            </Typography>
          ) : (
            indexes.map((index) => (
              <Box
                key={index.index_id}
                onClick={() => setSelectedId(index.index_id)}
                sx={{
                  p: 1,
                  border: 1,
                  borderColor: activeId === index.index_id ? "primary.main" : "divider",
                  borderRadius: 1,
                  cursor: "pointer",
                }}
              >
                <Typography sx={{ fontWeight: 600 }}>{index.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {index.documents.length} documents · {index.index_id.slice(0, 8)}
                </Typography>
              </Box>
            ))
          )}
        </Stack>

        {coverage ? (
          <Typography variant="caption" color="text.secondary" component="pre" sx={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(coverage.coverage, null, 2)}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import BackupIcon from "@mui/icons-material/Backup";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import {
  backupDownloadUrl,
  createBackup,
  deleteBackup,
  listBackups,
  restoreBackup,
  type BackupMeta,
} from "@/lib/admin-api";
import { buildApiHeaders } from "@/lib/ce-api";

export default function BackupAdminPage() {
  const [backups, setBackups] = React.useState<BackupMeta[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const restoreInputRef = React.useRef<HTMLInputElement>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setBackups(await listBackups());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load backups");
      setBackups([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      await createBackup();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backup failed");
    } finally {
      setBusy(false);
    }
  };

  const handleRestore = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      await restoreBackup(file);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Restore failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (backupId: string) => {
    setError(null);
    try {
      await deleteBackup(backupId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const handleDownload = async (backupId: string, filename?: string) => {
    setError(null);
    try {
      const response = await fetch(backupDownloadUrl(backupId), {
        headers: buildApiHeaders(),
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("Download failed");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename || `${backupId}.zip`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Backup and Restore"
        description="Create backups and restore workspace data."
        breadcrumbs={[
          { label: "Admin", href: "/admin/backup" },
          { label: "Backup" },
        ]}
        actions={
          <>
            <input
              ref={restoreInputRef}
              type="file"
              accept=".zip,application/zip"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  handleRestore(file);
                }
              }}
            />
            <Button variant="outlined" disabled={busy} onClick={() => restoreInputRef.current?.click()}>
              Restore from file
            </Button>
            <Button variant="contained" disabled={busy} onClick={handleCreate}>
              {busy ? "Working..." : "Create backup"}
            </Button>
          </>
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <SkeletonDetailPanel fields={4} />
      ) : backups.length === 0 ? (
        <EmptyState
          title="No backups yet"
          description="Create a backup to download workspace configuration and data."
          icon={<BackupIcon sx={{ fontSize: 48 }} />}
          actionLabel="Create backup"
          onAction={handleCreate}
        />
      ) : (
        <List sx={{ bgcolor: "background.paper", borderRadius: 1, border: 1, borderColor: "divider" }}>
          {backups.map((backup) => (
            <ListItem
              key={backup.id}
              secondaryAction={
                <Box>
                  <IconButton onClick={() => handleDownload(backup.id, backup.filename)} title="Download">
                    <DownloadIcon />
                  </IconButton>
                  <IconButton onClick={() => handleDelete(backup.id)} title="Delete">
                    <DeleteIcon />
                  </IconButton>
                </Box>
              }
            >
              <ListItemText
                primary={backup.filename || backup.id}
                secondary={
                  <>
                    {backup.created_at}
                    {backup.size_bytes ? ` | ${Math.round(backup.size_bytes / 1024)} KB` : ""}
                  </>
                }
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
}

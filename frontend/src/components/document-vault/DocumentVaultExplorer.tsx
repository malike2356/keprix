"use client";

/**
 * Tenant Document Vault explorer (Prompt 648).
 * Never mounts host filesystem paths; admin host browse stays on /files?mode=host.
 */

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import CreateNewFolderOutlinedIcon from "@mui/icons-material/CreateNewFolderOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import FolderIcon from "@mui/icons-material/Folder";
import GridViewIcon from "@mui/icons-material/GridView";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import RefreshIcon from "@mui/icons-material/Refresh";
import RestoreFromTrashIcon from "@mui/icons-material/RestoreFromTrash";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import ViewListIcon from "@mui/icons-material/ViewList";
import * as React from "react";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import {
  classifyVaultError,
  createVaultItem,
  exportVaultItem,
  fetchGoogleDriveConflicts,
  fetchGoogleDriveStatus,
  getVaultContent,
  importVaultFile,
  listVaultItems,
  moveVaultItem,
  patchVaultItem,
  resolveGoogleDriveConflict,
  restoreVaultItem,
  syncGoogleDrive,
  trashVaultItem,
  type VaultErrorState,
  type VaultItem,
} from "@/lib/document-vault-api";

type Crumb = { id: string | null; name: string };

type ExplorerProps = {
  /** When true, show admin link to host filesystem mode. */
  showHostFsLink?: boolean;
};

function humanSize(bytes?: number): string {
  if (!bytes || bytes <= 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function errorCopy(state: VaultErrorState): { title: string; body: string } {
  switch (state) {
    case "offline":
      return {
        title: "Offline",
        body: "Document Vault needs a network connection to the Keprix API. Retry when online.",
      };
    case "quota":
      return {
        title: "Quota or size limit",
        body: "This workspace cannot accept more data, or the upload exceeds the allowed size.",
      };
    case "conflict":
      return {
        title: "Revision conflict",
        body: "Another edit landed first. Reload the item, then save again.",
      };
    case "conversion":
      return {
        title: "Conversion failed",
        body: "Import or export could not complete. Check format support and try again.",
      };
    case "forbidden":
      return {
        title: "Not allowed",
        body: "This action is blocked for the current workspace. Host filesystem paths never enter the tenant vault.",
      };
    case "empty":
      return {
        title: "Empty folder",
        body: "Create a folder or note, or drop files here to import.",
      };
    case "loading":
      return { title: "Loading", body: "Fetching vault items..." };
    default:
      return {
        title: "Something went wrong",
        body: "The Document Vault request failed. Retry or check API flags.",
      };
  }
}

export default function DocumentVaultExplorer({ showHostFsLink = false }: ExplorerProps) {
  const [parentId, setParentId] = React.useState<string | null>(null);
  const [crumbs, setCrumbs] = React.useState<Crumb[]>([{ id: null, name: "Vault" }]);
  const [items, setItems] = React.useState<VaultItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [errorState, setErrorState] = React.useState<VaultErrorState | null>(null);
  const [errorDetail, setErrorDetail] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [showTrash, setShowTrash] = React.useState(false);
  const [view, setView] = React.useState<"list" | "grid">("list");
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set());
  const [preview, setPreview] = React.useState<{ item: VaultItem; content: string } | null>(null);
  const [createOpen, setCreateOpen] = React.useState<"folder" | "markdown" | null>(null);
  const [createName, setCreateName] = React.useState("");
  const [menuAnchor, setMenuAnchor] = React.useState<{ el: HTMLElement; item: VaultItem } | null>(
    null,
  );
  const [dragOver, setDragOver] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [driveStatus, setDriveStatus] = React.useState<Record<string, unknown> | null>(null);
  const [conflictCount, setConflictCount] = React.useState(0);
  const uploadRef = React.useRef<HTMLInputElement | null>(null);
  const dragSnapshot = React.useRef<VaultItem[] | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setErrorState(null);
    setErrorDetail(null);
    try {
      const result = await listVaultItems({
        parentId: search.trim() ? undefined : parentId,
        q: search.trim() || undefined,
        includeTrashed: showTrash,
        limit: 200,
      });
      const next = result.items || [];
      setItems(next);
      if (!next.length && !search.trim()) {
        setErrorState("empty");
      }
    } catch (err) {
      setItems([]);
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [parentId, search, showTrash]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const refreshDrive = React.useCallback(async () => {
    try {
      const status = await fetchGoogleDriveStatus();
      setDriveStatus(status);
      if (status.connected) {
        const conflicts = await fetchGoogleDriveConflicts();
        setConflictCount((conflicts.conflicts || []).length);
      } else {
        setConflictCount(0);
      }
    } catch {
      setDriveStatus(null);
    }
  }, []);

  React.useEffect(() => {
    void refreshDrive();
  }, [refreshDrive]);

  const openFolder = (item: VaultItem) => {
    if (item.kind !== "folder") return;
    setParentId(item.id);
    setCrumbs((prev) => [...prev, { id: item.id, name: item.name }]);
    setSelectedIds(new Set());
    setPreview(null);
    setSearch("");
  };

  const goCrumb = (index: number) => {
    const target = crumbs[index];
    setCrumbs(crumbs.slice(0, index + 1));
    setParentId(target.id);
    setSelectedIds(new Set());
    setPreview(null);
    setSearch("");
  };

  const openPreview = async (item: VaultItem) => {
    if (item.kind === "folder") {
      openFolder(item);
      return;
    }
    try {
      const payload = await getVaultContent(item.id);
      setPreview({ item, content: payload.content || "" });
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Preview failed");
    }
  };

  const runCreate = async () => {
    if (!createOpen || !createName.trim()) return;
    setBusy(true);
    try {
      await createVaultItem({
        kind: createOpen === "folder" ? "folder" : "markdown",
        name: createName.trim(),
        parent_id: parentId,
        content: createOpen === "markdown" ? "# " + createName.trim() + "\n\n" : undefined,
      });
      setCreateOpen(null);
      setCreateName("");
      setMessage(createOpen === "folder" ? "Folder created." : "Note created.");
      await load();
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  const toggleSelect = (id: string, additive: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(additive ? prev : []);
      if (next.has(id) && additive) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const onTrash = async (item: VaultItem) => {
    setBusy(true);
    try {
      await trashVaultItem(item.id);
      setMessage(`Moved ${item.name} to trash.`);
      setMenuAnchor(null);
      if (preview?.item.id === item.id) setPreview(null);
      await load();
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Trash failed");
    } finally {
      setBusy(false);
    }
  };

  const onRestore = async (item: VaultItem) => {
    setBusy(true);
    try {
      await restoreVaultItem(item.id);
      setMessage(`Restored ${item.name}.`);
      setMenuAnchor(null);
      await load();
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Restore failed");
    } finally {
      setBusy(false);
    }
  };

  const onFavorite = async (item: VaultItem) => {
    try {
      await patchVaultItem(item.id, { is_favorite: !item.is_favorite });
      await load();
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Favorite failed");
    }
  };

  const onRename = async (item: VaultItem) => {
    const name = window.prompt("Rename item", item.name);
    if (!name || name.trim() === item.name) return;
    try {
      await patchVaultItem(item.id, { name: name.trim() });
      setMenuAnchor(null);
      await load();
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Rename failed");
    }
  };

  const onExport = async (item: VaultItem, format: string) => {
    try {
      const blob = await exportVaultItem(item.id, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${item.name}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      setMenuAnchor(null);
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Export failed");
    }
  };

  const handleUploadFiles = async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    setBusy(true);
    try {
      for (const file of list) {
        await importVaultFile(file, parentId);
      }
      setMessage(`Imported ${list.length} file(s).`);
      await load();
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  const onDragStartItem = (event: React.DragEvent, item: VaultItem) => {
    event.dataTransfer.setData("application/x-keprix-vault-id", item.id);
    event.dataTransfer.setData("text/plain", item.id);
    event.dataTransfer.effectAllowed = "move";
    dragSnapshot.current = items;
  };

  const onDropOnFolder = async (event: React.DragEvent, folder: VaultItem) => {
    event.preventDefault();
    event.stopPropagation();
    setDragOver(false);
    if (folder.kind !== "folder") return;
    const itemId = event.dataTransfer.getData("application/x-keprix-vault-id");
    if (!itemId || itemId === folder.id) return;
    const previous = dragSnapshot.current;
    setItems((curr) => curr.filter((row) => row.id !== itemId));
    try {
      await moveVaultItem(itemId, folder.id);
      setMessage("Moved item.");
      await load();
    } catch (err) {
      if (previous) setItems(previous);
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Move failed; rolled back.");
    }
  };

  const onDropUpload = async (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
    const vaultId = event.dataTransfer.getData("application/x-keprix-vault-id");
    if (vaultId) return;
    if (event.dataTransfer.files?.length) {
      await handleUploadFiles(event.dataTransfer.files);
    }
  };

  const savePreview = async () => {
    if (!preview) return;
    setBusy(true);
    try {
      await patchVaultItem(preview.item.id, {
        content: preview.content,
        expected_revision: preview.item.current_revision,
      });
      setMessage("Saved.");
      const refreshed = await listVaultItems({ parentId, includeTrashed: showTrash });
      const match = refreshed.items.find((row) => row.id === preview.item.id);
      if (match) setPreview({ item: match, content: preview.content });
      await load();
    } catch (err) {
      setErrorState(classifyVaultError(err));
      setErrorDetail(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const folders = items.filter((item) => item.kind === "folder" && !item.trashed);
  const copy = errorState ? errorCopy(errorState) : null;

  return (
    <Box>
      <PageHeader
        title="Document Vault"
        description="Tenant virtual filesystem. Separate from admin host filesystem browsing."
        breadcrumbs={[
          { label: "Workspace", href: "/" },
          { label: "Document Vault" },
        ]}
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              size="small"
              startIcon={<CreateNewFolderOutlinedIcon />}
              onClick={() => {
                setCreateName("New folder");
                setCreateOpen("folder");
              }}
            >
              Folder
            </Button>
            <Button
              size="small"
              startIcon={<DescriptionOutlinedIcon />}
              onClick={() => {
                setCreateName("Untitled");
                setCreateOpen("markdown");
              }}
            >
              Note
            </Button>
            <Button
              size="small"
              startIcon={<UploadFileOutlinedIcon />}
              onClick={() => uploadRef.current?.click()}
            >
              Upload
            </Button>
            <Button size="small" startIcon={<RefreshIcon />} onClick={() => void load()} disabled={loading}>
              Refresh
            </Button>
            {showHostFsLink ? (
              <Button size="small" href="/files?mode=host" component="a" variant="outlined">
                Admin host FS
              </Button>
            ) : null}
          </Stack>
        }
      />

      <input
        ref={uploadRef}
        type="file"
        hidden
        multiple
        onChange={(event) => {
          if (event.target.files) void handleUploadFiles(event.target.files);
          event.target.value = "";
        }}
      />

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mb: 2 }} alignItems="center">
        <TextField
          size="small"
          placeholder="Search vault..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          sx={{ minWidth: 220, flex: 1 }}
          inputProps={{ "aria-label": "Search Document Vault" }}
        />
        <Button
          size="small"
          variant={showTrash ? "contained" : "outlined"}
          startIcon={<DeleteOutlineIcon />}
          onClick={() => setShowTrash((value) => !value)}
        >
          Trash
        </Button>
        <Button
          size="small"
          variant="outlined"
          disabled={busy}
          onClick={() => {
            void (async () => {
              setBusy(true);
              try {
                await syncGoogleDrive({ direction: "inbound", source: "manual" });
                setMessage("Google Drive sync finished.");
                await refreshDrive();
                await load();
              } catch (err) {
                setErrorState(classifyVaultError(err));
                setErrorDetail(err instanceof Error ? err.message : "Sync failed");
              } finally {
                setBusy(false);
              }
            })();
          }}
        >
          Sync Drive
        </Button>
        <Chip
          size="small"
          label={
            driveStatus?.connected
              ? `Drive: ${String(driveStatus.mode || "connected")}${conflictCount ? ` · ${conflictCount} conflicts` : ""}`
              : "Drive: not connected"
          }
          color={conflictCount ? "warning" : driveStatus?.connected ? "success" : "default"}
          variant="outlined"
        />
        <ToggleButtonGroup
          size="small"
          exclusive
          value={view}
          onChange={(_, next) => next && setView(next)}
          aria-label="Vault view mode"
        >
          <ToggleButton value="list" aria-label="List view">
            <ViewListIcon fontSize="small" />
          </ToggleButton>
          <ToggleButton value="grid" aria-label="Grid view">
            <GridViewIcon fontSize="small" />
          </ToggleButton>
        </ToggleButtonGroup>
        <Chip size="small" label="Tenant Vault" color="primary" variant="outlined" />
      </Stack>

      {conflictCount > 0 ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {conflictCount} Google Drive conflict(s). Both versions are preserved. Resolve via API
          choice keep_local / keep_remote / keep_both (UI resolve uses keep_both by default).
          <Button
            size="small"
            sx={{ ml: 1 }}
            onClick={() => {
              void (async () => {
                const payload = await fetchGoogleDriveConflicts();
                const first = (payload.conflicts || [])[0] as { item_id?: string } | undefined;
                if (first?.item_id) {
                  await resolveGoogleDriveConflict(first.item_id, "keep_both");
                  setMessage("Conflict marked keep_both.");
                  await refreshDrive();
                  await load();
                }
              })();
            }}
          >
            Keep both (first)
          </Button>
        </Alert>
      ) : null}

      <Breadcrumbs sx={{ mb: 2 }} aria-label="Vault breadcrumbs">
        {crumbs.map((crumb, index) =>
          index === crumbs.length - 1 ? (
            <Typography key={`${crumb.id}-${index}`} color="text.primary">
              {crumb.name}
            </Typography>
          ) : (
            <Link
              key={`${crumb.id}-${index}`}
              component="button"
              type="button"
              underline="hover"
              color="inherit"
              onClick={() => goCrumb(index)}
            >
              {crumb.name}
            </Link>
          ),
        )}
      </Breadcrumbs>

      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {errorState && errorState !== "empty" ? (
        <Alert
          severity={errorState === "offline" ? "warning" : "error"}
          sx={{ mb: 2 }}
          onClose={() => {
            setErrorState(null);
            setErrorDetail(null);
          }}
        >
          <strong>{copy?.title}</strong>
          {": "}
          {copy?.body}
          {errorDetail ? ` (${errorDetail})` : ""}
        </Alert>
      ) : null}

      <Box
        onDragOver={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(event) => void onDropUpload(event)}
        sx={{
          border: "1px dashed",
          borderColor: dragOver ? "primary.main" : "divider",
          borderRadius: 2,
          bgcolor: dragOver ? "action.hover" : "background.paper",
          minHeight: 320,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: preview ? "1fr 1fr" : "240px 1fr" },
          gap: 0,
        }}
      >
        <Box sx={{ borderRight: "1px solid", borderColor: "divider", p: 1, maxHeight: 520, overflow: "auto" }}>
          <Typography variant="caption" color="text.secondary" sx={{ px: 1 }}>
            Folders
          </Typography>
          <List dense>
            <ListItemButton
              selected={parentId === null}
              onClick={() => {
                setCrumbs([{ id: null, name: "Vault" }]);
                setParentId(null);
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                <FolderIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Root" />
            </ListItemButton>
            {folders.map((folder) => (
              <ListItemButton
                key={folder.id}
                selected={parentId === folder.id}
                onClick={() => openFolder(folder)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => void onDropOnFolder(event, folder)}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <FolderIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText primary={folder.name} />
              </ListItemButton>
            ))}
          </List>
        </Box>

        <Box sx={{ p: 2, minHeight: 280 }}>
          {loading ? (
            <SkeletonList rows={6} />
          ) : errorState === "empty" && !items.length ? (
            <EmptyState
              title={copy?.title || "Empty"}
              description={copy?.body || "No items"}
              actionLabel="New note"
              onAction={() => {
                setCreateName("Untitled");
                setCreateOpen("markdown");
              }}
            />
          ) : view === "grid" ? (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                gap: 1.5,
              }}
            >
              {items.map((item) => (
                <Box
                  key={item.id}
                  draggable={!item.trashed}
                  onDragStart={(event) => onDragStartItem(event, item)}
                  onDragOver={(event) => item.kind === "folder" && event.preventDefault()}
                  onDrop={(event) => item.kind === "folder" && void onDropOnFolder(event, item)}
                  onClick={(event) => {
                    if (event.metaKey || event.ctrlKey) toggleSelect(item.id, true);
                    else void openPreview(item);
                  }}
                  sx={{
                    p: 1.5,
                    border: "1px solid",
                    borderColor: selectedIds.has(item.id) ? "primary.main" : "divider",
                    borderRadius: 1,
                    cursor: "pointer",
                    bgcolor: selectedIds.has(item.id) ? "action.selected" : "transparent",
                  }}
                >
                  {item.kind === "folder" ? <FolderIcon /> : <DescriptionOutlinedIcon />}
                  <Typography variant="body2" noWrap>
                    {item.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {item.kind}
                    {item.trashed ? " · trash" : ""}
                  </Typography>
                </Box>
              ))}
            </Box>
          ) : (
            <List dense>
              {items.map((item) => (
                <ListItemButton
                  key={item.id}
                  selected={selectedIds.has(item.id) || preview?.item.id === item.id}
                  draggable={!item.trashed}
                  onDragStart={(event) => onDragStartItem(event, item)}
                  onDragOver={(event) => item.kind === "folder" && event.preventDefault()}
                  onDrop={(event) => item.kind === "folder" && void onDropOnFolder(event, item)}
                  onClick={(event) => {
                    if (event.metaKey || event.ctrlKey) toggleSelect(item.id, true);
                    else void openPreview(item);
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {item.kind === "folder" ? (
                      <FolderIcon fontSize="small" />
                    ) : (
                      <DescriptionOutlinedIcon fontSize="small" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.name}
                    secondary={`${item.kind}${humanSize(item.byte_size) ? ` · ${humanSize(item.byte_size)}` : ""}${
                      item.trashed ? " · trash" : ""
                    }`}
                  />
                  <IconButton
                    size="small"
                    aria-label={item.is_favorite ? "Unfavorite" : "Favorite"}
                    onClick={(event) => {
                      event.stopPropagation();
                      void onFavorite(item);
                    }}
                  >
                    {item.is_favorite ? <StarIcon fontSize="small" /> : <StarBorderIcon fontSize="small" />}
                  </IconButton>
                  <IconButton
                    size="small"
                    aria-label="Item menu"
                    onClick={(event) => {
                      event.stopPropagation();
                      setMenuAnchor({ el: event.currentTarget, item });
                    }}
                  >
                    <MoreVertIcon fontSize="small" />
                  </IconButton>
                </ListItemButton>
              ))}
            </List>
          )}

          {preview && preview.item.kind !== "folder" ? (
            <>
              <Divider sx={{ my: 2 }} />
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="subtitle2">{preview.item.name}</Typography>
                <Button size="small" variant="contained" disabled={busy} onClick={() => void savePreview()}>
                  Save
                </Button>
              </Stack>
              <TextField
                multiline
                minRows={10}
                fullWidth
                value={preview.content}
                onChange={(event) => setPreview({ ...preview, content: event.target.value })}
                inputProps={{ "aria-label": "Document content" }}
              />
            </>
          ) : null}
        </Box>
      </Box>

      <Menu
        anchorEl={menuAnchor?.el}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        <MenuItem
          onClick={() => menuAnchor && void onRename(menuAnchor.item)}
          disabled={Boolean(menuAnchor?.item.trashed)}
        >
          Rename
        </MenuItem>
        <MenuItem
          onClick={() => menuAnchor && void onExport(menuAnchor.item, "md")}
          disabled={menuAnchor?.item.kind === "folder"}
        >
          Export markdown
        </MenuItem>
        <MenuItem
          onClick={() => menuAnchor && void onExport(menuAnchor.item, "pdf")}
          disabled={menuAnchor?.item.kind === "folder"}
        >
          Export PDF
        </MenuItem>
        {menuAnchor?.item.trashed ? (
          <MenuItem onClick={() => menuAnchor && void onRestore(menuAnchor.item)}>
            <RestoreFromTrashIcon fontSize="small" sx={{ mr: 1 }} /> Restore
          </MenuItem>
        ) : (
          <MenuItem onClick={() => menuAnchor && void onTrash(menuAnchor.item)}>
            <DeleteOutlineIcon fontSize="small" sx={{ mr: 1 }} /> Move to trash
          </MenuItem>
        )}
      </Menu>

      <Dialog open={Boolean(createOpen)} onClose={() => setCreateOpen(null)} fullWidth maxWidth="xs">
        <DialogTitle>{createOpen === "folder" ? "New folder" : "New note"}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label="Name"
            value={createName}
            onChange={(event) => setCreateName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void runCreate();
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(null)}>Cancel</Button>
          <Button variant="contained" disabled={busy || !createName.trim()} onClick={() => void runCreate()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export { errorCopy };

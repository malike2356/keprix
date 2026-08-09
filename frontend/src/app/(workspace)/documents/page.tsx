"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import FolderIcon from "@mui/icons-material/Folder";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import * as React from "react";
import DocumentAgentPanel from "@/components/documents/DocumentAgentPanel";
import IndexManagerPanel from "@/components/documents/IndexManagerPanel";
import StructuredDataView from "@/components/ui/StructuredDataView";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel, SkeletonList } from "@/components/ui/loading";
import MarkdownRenderer from "@/components/workspace/MarkdownRenderer";
import {
  aiEditDocument,
  aiSuggestDocument,
  createDocument,
  deleteDocument,
  exportDocument,
  fetchDocuments,
  fetchDocumentVersions,
  importDocumentFile,
  importDocumentFromPath,
  patchDocumentMeta,
  restoreDocumentVersion,
  shareDocument,
  updateDocument,
  type WorkspaceDocument,
} from "@/lib/workspace-api";
import { extractDocumentStructure } from "@/lib/documents-api";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function DocumentsPage() {
  const [documents, setDocuments] = React.useState<WorkspaceDocument[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [tagsInput, setTagsInput] = React.useState("");
  const [folderInput, setFolderInput] = React.useState("");
  const [diskPath, setDiskPath] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const [favoritesOnly, setFavoritesOnly] = React.useState(false);
  const [folderFilter, setFolderFilter] = React.useState("");
  const [viewTab, setViewTab] = React.useState(0);
  const [editorTab, setEditorTab] = React.useState(0);
  const [showAdvanced, setShowAdvanced] = React.useState(false);
  const [aiInstruction, setAiInstruction] = React.useState("");
  const [suggestions, setSuggestions] = React.useState<string[]>([]);
  const [versions, setVersions] = React.useState<
    Array<{ id: string; title: string; content: string; created_at: string }>
  >([]);
  const [extractResult, setExtractResult] = React.useState<Record<string, unknown> | null>(null);
  const autosaveTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const selected = documents.find((doc) => doc.id === selectedId) ?? null;

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchDocuments({
        q: search.trim() || undefined,
        favorites: favoritesOnly || undefined,
        folder: folderFilter || undefined,
      });
      setDocuments(items);
      setSelectedId((prev) => {
        if (prev && items.some((item) => item.id === prev)) return prev;
        return items[0]?.id ?? null;
      });
    } catch (err) {
      setDocuments([]);
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [search, favoritesOnly, folderFilter]);

  React.useEffect(() => {
    void load();
  }, [load]);

  React.useEffect(() => {
    if (!selected || !dirty) return;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(() => {
      void (async () => {
        try {
          setSaving(true);
          const updated = await updateDocument(selected.id, {
            title: selected.title,
            content: selected.content,
            tags: selected.tags,
          });
          setDocuments((prev) => prev.map((doc) => (doc.id === updated.id ? updated : doc)));
          setDirty(false);
          setMessage("Autosaved");
        } catch (err) {
          setError(err instanceof Error ? err.message : "Autosave failed");
        } finally {
          setSaving(false);
        }
      })();
    }, 1200);
    return () => {
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    };
  }, [selected, dirty]);

  function updateSelected(patch: Partial<WorkspaceDocument>) {
    if (!selected) return;
    setDocuments((prev) =>
      prev.map((doc) => (doc.id === selected.id ? { ...doc, ...patch } : doc)),
    );
    setDirty(true);
  }

  async function handleCreate() {
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const doc = await createDocument({
        title: title.trim(),
        content,
        tags: tagsInput
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        folder: folderInput.trim(),
      });
      setDocuments((prev) => [doc, ...prev]);
      setSelectedId(doc.id);
      setDialogOpen(false);
      setTitle("");
      setContent("");
      setTagsInput("");
      setFolderInput("");
      setMessage("Document created");
      setDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create document");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveSelected() {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateDocument(selected.id, {
        title: selected.title,
        content: selected.content,
        tags: selected.tags,
      });
      setDocuments((prev) => prev.map((doc) => (doc.id === updated.id ? updated : doc)));
      setDirty(false);
      setMessage("Saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save document");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteSelected() {
    if (!selected) return;
    if (!window.confirm(`Delete "${selected.title}"?`)) return;
    setSaving(true);
    try {
      await deleteDocument(selected.id);
      await load();
      setDirty(false);
      setMessage("Deleted");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document");
    } finally {
      setSaving(false);
    }
  }

  async function handleExport(format: "md" | "html" | "txt" | "pdf") {
    if (!selected) return;
    try {
      const blob = await exportDocument(selected.id, format);
      downloadBlob(blob, `${selected.title || "document"}.${format === "md" ? "md" : format}`);
      setMessage(`Exported as ${format}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  }

  async function handleShare() {
    if (!selected) return;
    try {
      const result = await shareDocument(selected.id);
      const url = `${window.location.origin}${result.path}`;
      await navigator.clipboard.writeText(url);
      setMessage(`Share link copied: ${url}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Share failed");
    }
  }

  async function handleFavorite() {
    if (!selected) return;
    try {
      const updated = await patchDocumentMeta(selected.id, {
        is_favorite: !selected.is_favorite,
      });
      setDocuments((prev) => prev.map((doc) => (doc.id === updated.id ? updated : doc)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update favorite");
    }
  }

  async function handleImport(file?: File | null) {
    if (!file) return;
    setSaving(true);
    setError(null);
    try {
      const doc = await importDocumentFile(file);
      setDocuments((prev) => [doc, ...prev]);
      setSelectedId(doc.id);
      setMessage(`Imported ${file.name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleImportPath() {
    if (!diskPath.trim()) {
      setError("Enter a server disk path under an allowed root");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const doc = await importDocumentFromPath(diskPath.trim());
      setDocuments((prev) => [doc, ...prev]);
      setSelectedId(doc.id);
      setDiskPath("");
      setMessage(`Imported from disk: ${doc.title}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import from path failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleAiEdit() {
    if (!selected || !aiInstruction.trim()) return;
    setSaving(true);
    try {
      const result = await aiEditDocument(selected.id, aiInstruction.trim());
      updateSelected({ content: result.content });
      setMessage("AI edit applied (review before sharing)");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI edit failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleAiSuggest() {
    if (!selected) return;
    try {
      const result = await aiSuggestDocument(selected.id);
      setSuggestions(result.suggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI suggest failed");
    }
  }

  async function handleLoadVersions() {
    if (!selected) return;
    try {
      setVersions(await fetchDocumentVersions(selected.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load versions");
    }
  }

  async function handleRestore(versionId: string) {
    if (!selected) return;
    try {
      const updated = await restoreDocumentVersion(selected.id, versionId);
      setDocuments((prev) => prev.map((doc) => (doc.id === updated.id ? updated : doc)));
      setDirty(false);
      setMessage("Version restored");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Restore failed");
    }
  }

  async function handleExtract() {
    if (!selected) return;
    try {
      const result = await extractDocumentStructure(selected.content);
      setExtractResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extract failed");
    }
  }

  function openInChat() {
    if (!selected) return;
    const q = encodeURIComponent(`Use this document titled "${selected.title}":\n\n${selected.content.slice(0, 4000)}`);
    window.location.href = `/chat?prefill=${q}`;
  }

  const folders = Array.from(
    new Set(documents.map((doc) => doc.folder || "").filter(Boolean)),
  ).sort();

  return (
    <Box>
      <PageHeader
        title="Documents"
        description="Durable markdown docs with preview, import/export, AI helpers, versions, and ask-over-docs."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Documents", href: "/documents" },
        ]}
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button variant="contained" onClick={() => setDialogOpen(true)}>
              New document
            </Button>
            <Button component="label" variant="outlined">
              Import file
              <input
                hidden
                type="file"
                accept=".md,.txt,.markdown,.csv,.html,.htm,.docx,.pdf"
                onChange={(e) => void handleImport(e.target.files?.[0])}
              />
            </Button>
          </Stack>
        }
      />

      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Box
        sx={{
          mb: 2,
          p: 1.5,
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          display: "grid",
          gap: 1,
          maxWidth: 720,
        }}
      >
        <Typography variant="subtitle2">Import from server disk path</Typography>
        <Typography variant="body2" color="text.secondary">
          Path must be inside an allowed root (KEPRIX_HOME / KEPRIX_DATA_DIR / /data/keprix). In Docker, put files on the
          bind-mounted data volume first.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField
            size="small"
            fullWidth
            label="Absolute server path"
            value={diskPath}
            onChange={(e) => setDiskPath(e.target.value)}
            placeholder="/data/keprix/docs/notes.md"
          />
          <Button variant="outlined" onClick={() => void handleImportPath()} disabled={saving}>
            Import path
          </Button>
        </Stack>
      </Box>

      <Tabs value={viewTab} onChange={(_, value) => setViewTab(value)} sx={{ mb: 2 }}>
        <Tab label="Library" />
        <Tab label="Ask / Indexes" />
      </Tabs>

      {viewTab === 1 ? (
        <Box sx={{ display: "grid", gap: 2 }}>
          <IndexManagerPanel />
          <DocumentAgentPanel />
        </Box>
      ) : null}

      {viewTab === 0 ? (
        <>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mb: 2 }} alignItems="center">
            <TextField
              size="small"
              label="Search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              sx={{ minWidth: 220 }}
            />
            <TextField
              size="small"
              label="Folder filter"
              value={folderFilter}
              onChange={(e) => setFolderFilter(e.target.value)}
              placeholder="e.g. projects"
              sx={{ minWidth: 160 }}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={favoritesOnly}
                  onChange={(e) => setFavoritesOnly(e.target.checked)}
                />
              }
              label="Favorites only"
            />
            {folders.length ? (
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                {folders.map((folder) => (
                  <Chip
                    key={folder}
                    size="small"
                    label={folder}
                    onClick={() => setFolderFilter(folder)}
                    variant={folderFilter === folder ? "filled" : "outlined"}
                  />
                ))}
              </Stack>
            ) : null}
          </Stack>

          {loading ? (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "280px 1fr" }, gap: 2 }}>
              <SkeletonList rows={8} rowHeight={48} />
              <SkeletonDetailPanel fields={4} />
            </Box>
          ) : documents.length === 0 ? (
            <EmptyState
              title="No documents"
              description="Create a markdown document, or import .md / .txt / .docx / PDF. Documents now persist in Postgres."
              icon={<FolderIcon sx={{ fontSize: 48 }} />}
              actionLabel="New document"
              onAction={() => setDialogOpen(true)}
            />
          ) : (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "280px 1fr" }, gap: 2 }}>
              <List dense sx={{ bgcolor: "background.paper", borderRadius: 1, border: 1, borderColor: "divider" }}>
                {documents.map((doc) => (
                  <ListItemButton
                    key={doc.id}
                    selected={doc.id === selectedId}
                    onClick={() => {
                      setSelectedId(doc.id);
                      setDirty(false);
                      setSuggestions([]);
                      setVersions([]);
                      setExtractResult(null);
                    }}
                  >
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <span>{doc.title || "Untitled"}</span>
                          {doc.is_favorite ? <StarIcon fontSize="inherit" color="warning" /> : null}
                        </Stack>
                      }
                      secondary={`${doc.word_count ?? 0} words${doc.folder ? ` · ${doc.folder}` : ""}${dirty && doc.id === selectedId ? " · unsaved" : ""}`}
                    />
                  </ListItemButton>
                ))}
              </List>

              {selected ? (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <TextField
                      label="Title"
                      value={selected.title}
                      onChange={(e) => updateSelected({ title: e.target.value })}
                      sx={{ flex: 1, minWidth: 200 }}
                    />
                    <IconButton onClick={() => void handleFavorite()} aria-label="Favorite">
                      {selected.is_favorite ? <StarIcon color="warning" /> : <StarBorderIcon />}
                    </IconButton>
                    <Chip size="small" label={dirty ? "Unsaved" : saving ? "Saving…" : "Saved"} />
                  </Stack>

                  <TextField
                    size="small"
                    label="Tags (comma separated)"
                    value={(selected.tags || []).join(", ")}
                    onChange={(e) =>
                      updateSelected({
                        tags: e.target.value
                          .split(",")
                          .map((t) => t.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                  <TextField
                    size="small"
                    label="Folder"
                    value={selected.folder || ""}
                    onChange={(e) => updateSelected({ folder: e.target.value })}
                    onBlur={() => {
                      void patchDocumentMeta(selected.id, { folder: selected.folder || "" })
                        .then((updated) => {
                          setDocuments((prev) =>
                            prev.map((doc) => (doc.id === updated.id ? { ...doc, ...updated } : doc)),
                          );
                        })
                        .catch((err) =>
                          setError(err instanceof Error ? err.message : "Folder update failed"),
                        );
                    }}
                  />

                  <Tabs value={editorTab} onChange={(_, value) => setEditorTab(value)}>
                    <Tab label="Edit" />
                    <Tab label="Preview" />
                    <Tab label="Split" />
                  </Tabs>

                  {editorTab === 0 || editorTab === 2 ? (
                    <TextField
                      label="Content"
                      value={selected.content}
                      onChange={(e) => updateSelected({ content: e.target.value })}
                      multiline
                      minRows={editorTab === 2 ? 10 : 14}
                    />
                  ) : null}
                  {editorTab === 1 || editorTab === 2 ? (
                    <Box
                      sx={{
                        border: 1,
                        borderColor: "divider",
                        borderRadius: 1,
                        p: 2,
                        minHeight: 180,
                      }}
                    >
                      <MarkdownRenderer content={selected.content || "_Empty document_"} />
                    </Box>
                  ) : null}

                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Button variant="contained" onClick={() => void handleSaveSelected()} disabled={saving}>
                      Save
                    </Button>
                    <Button variant="outlined" onClick={() => void handleExport("md")}>
                      Export MD
                    </Button>
                    <Button variant="outlined" onClick={() => void handleExport("pdf")}>
                      Export PDF
                    </Button>
                    <Button variant="outlined" component="a" href="/data?tab=export">
                      Cover / signatory export
                    </Button>
                    <Button variant="outlined" onClick={() => void handleShare()}>
                      Share link
                    </Button>
                    <Button variant="outlined" onClick={openInChat}>
                      Open in chat
                    </Button>
                    <Button variant="outlined" color="error" onClick={() => void handleDeleteSelected()} disabled={saving}>
                      Delete
                    </Button>
                    <Button variant="text" onClick={() => setShowAdvanced((v) => !v)}>
                      {showAdvanced ? "Hide tools" : "AI / versions / extract"}
                    </Button>
                  </Stack>

                  <Collapse in={showAdvanced}>
                    <Box sx={{ display: "grid", gap: 1.5, p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
                      <Typography variant="subtitle2">AI helpers</Typography>
                      <TextField
                        size="small"
                        label="Edit instruction"
                        value={aiInstruction}
                        onChange={(e) => setAiInstruction(e.target.value)}
                        placeholder="Add a summary section at the top"
                      />
                      <Stack direction="row" spacing={1}>
                        <Button size="small" variant="outlined" onClick={() => void handleAiEdit()}>
                          Apply AI edit
                        </Button>
                        <Button size="small" variant="outlined" onClick={() => void handleAiSuggest()}>
                          Suggest improvements
                        </Button>
                        <Button size="small" variant="outlined" onClick={() => void handleExtract()}>
                          Structured extract
                        </Button>
                        <Button size="small" variant="outlined" onClick={() => void handleLoadVersions()}>
                          Load versions
                        </Button>
                      </Stack>
                      {suggestions.length ? (
                        <Box>
                          {suggestions.map((item) => (
                            <Typography key={item} variant="body2">
                              • {item}
                            </Typography>
                          ))}
                        </Box>
                      ) : null}
                      {extractResult ? <StructuredDataView value={extractResult} /> : null}
                      {versions.length ? (
                        <Box>
                          <Typography variant="subtitle2" sx={{ mb: 1 }}>
                            Versions
                          </Typography>
                          {versions.map((version) => (
                            <Stack
                              key={version.id}
                              direction="row"
                              spacing={1}
                              alignItems="center"
                              sx={{ mb: 0.5 }}
                            >
                              <Typography variant="body2" sx={{ flex: 1 }}>
                                {new Date(version.created_at).toLocaleString()} · {version.title}
                              </Typography>
                              <Button size="small" onClick={() => void handleRestore(version.id)}>
                                Restore
                              </Button>
                            </Stack>
                          ))}
                        </Box>
                      ) : null}
                    </Box>
                  </Collapse>
                </Box>
              ) : null}
            </Box>
          )}
        </>
      ) : null}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New document</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          <TextField
            label="Content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            multiline
            minRows={6}
          />
          <TextField
            label="Tags (comma separated)"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
          />
          <TextField
            label="Folder"
            value={folderInput}
            onChange={(e) => setFolderInput(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void handleCreate()} disabled={saving || !title.trim()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
      <Divider sx={{ my: 2 }} />
    </Box>
  );
}

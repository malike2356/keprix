"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import DownloadIcon from "@mui/icons-material/Download";
import FavoriteIcon from "@mui/icons-material/Favorite";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import ImageIcon from "@mui/icons-material/Image";
import RotateRightIcon from "@mui/icons-material/RotateRight";
import StarIcon from "@mui/icons-material/Star";
import TextSnippetOutlinedIcon from "@mui/icons-material/TextSnippetOutlined";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonBlock } from "@/components/ui/loading";
import {
  bulkDeleteGalleryImages,
  deleteGalleryImage,
  fetchGalleryImageObjectUrl,
  fetchGalleryImages,
  humanSize,
  importGalleryImageToDocuments,
  ocrGalleryImage,
  patchGalleryImage,
  uploadGalleryImage,
  type GalleryImage,
} from "@/lib/gallery-api";

export default function GalleryPage() {
  const [images, setImages] = React.useState<GalleryImage[]>([]);
  const [folders, setFolders] = React.useState<string[]>([]);
  const [previewUrls, setPreviewUrls] = React.useState<Record<string, string>>({});
  const [loading, setLoading] = React.useState(true);
  const [uploading, setUploading] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [folderFilter, setFolderFilter] = React.useState("");
  const [favoritesOnly, setFavoritesOnly] = React.useState(false);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [active, setActive] = React.useState<GalleryImage | null>(null);
  const [draftTitle, setDraftTitle] = React.useState("");
  const [draftFolder, setDraftFolder] = React.useState("");
  const [draftTags, setDraftTags] = React.useState("");
  const [brightness, setBrightness] = React.useState(100);
  const [contrast, setContrast] = React.useState(100);
  const [rotation, setRotation] = React.useState(0);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const previewUrlsRef = React.useRef<Record<string, string>>({});

  const revokePreviewUrls = React.useCallback((urls: Record<string, string>) => {
    for (const value of Object.values(urls)) {
      URL.revokeObjectURL(value);
    }
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGalleryImages({
        q: query.trim() || undefined,
        folder: folderFilter || undefined,
        favorites: favoritesOnly || undefined,
      });
      setImages(data.items);
      setFolders(data.folders || []);
    } catch (err) {
      setImages([]);
      setError(err instanceof Error ? err.message : "Failed to load gallery");
    } finally {
      setLoading(false);
    }
  }, [favoritesOnly, folderFilter, query]);

  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 200);
    return () => window.clearTimeout(timer);
  }, [load]);

  React.useEffect(() => {
    let cancelled = false;
    const previous = previewUrlsRef.current;

    async function hydratePreviews() {
      const next: Record<string, string> = {};
      await Promise.all(
        images.map(async (image) => {
          if (previous[image.id]) {
            next[image.id] = previous[image.id];
            return;
          }
          try {
            const url = await fetchGalleryImageObjectUrl(image);
            if (!cancelled) {
              next[image.id] = url;
            } else {
              URL.revokeObjectURL(url);
            }
          } catch {
            // Leave missing; tile shows placeholder.
          }
        }),
      );
      if (cancelled) {
        revokePreviewUrls(next);
        return;
      }
      const recycled = new Set(Object.values(next));
      const stale: Record<string, string> = {};
      for (const [id, url] of Object.entries(previous)) {
        if (!recycled.has(url)) {
          stale[id] = url;
        }
      }
      revokePreviewUrls(stale);
      previewUrlsRef.current = next;
      setPreviewUrls(next);
    }

    void hydratePreviews();
    return () => {
      cancelled = true;
    };
  }, [images, revokePreviewUrls]);

  React.useEffect(() => {
    return () => {
      revokePreviewUrls(previewUrlsRef.current);
      previewUrlsRef.current = {};
    };
  }, [revokePreviewUrls]);

  const activePreview = active ? previewUrls[active.id] : undefined;

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploading(true);
    setError(null);
    try {
      const uploaded: GalleryImage[] = [];
      for (const file of Array.from(files)) {
        if (!file.type.startsWith("image/")) continue;
        uploaded.push(
          await uploadGalleryImage(file, {
            folder: folderFilter || undefined,
          }),
        );
      }
      setStatus(`Uploaded ${uploaded.length} image${uploaded.length === 1 ? "" : "s"}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const openEditor = (image: GalleryImage) => {
    setActive(image);
    setDraftTitle(image.title || image.original_name || image.filename);
    setDraftFolder(image.folder || "");
    setDraftTags((image.tags || []).join(", "));
    setBrightness(100);
    setContrast(100);
    setRotation(0);
    setEditorOpen(true);
  };

  const toggleSelect = (id: string) => {
    setSelected((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDelete = async (imageId: string) => {
    setError(null);
    try {
      await deleteGalleryImage(imageId);
      setSelected((previous) => {
        const next = new Set(previous);
        next.delete(imageId);
        return next;
      });
      if (active?.id === imageId) {
        setEditorOpen(false);
        setActive(null);
      }
      setStatus("Deleted");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const handleBulkDelete = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      const removed = await bulkDeleteGalleryImages([...selected]);
      setSelected(new Set());
      setStatus(`Removed ${removed} image${removed === 1 ? "" : "s"}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk delete failed");
    } finally {
      setBusy(false);
    }
  };

  const saveMeta = async () => {
    if (!active) return;
    setBusy(true);
    setError(null);
    try {
      const item = await patchGalleryImage(active.id, {
        title: draftTitle,
        folder: draftFolder,
        tags: draftTags
          .split(",")
          .map((part) => part.trim())
          .filter(Boolean),
      });
      setActive(item);
      setStatus("Saved details");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const toggleFavorite = async (image: GalleryImage, event?: React.MouseEvent) => {
    event?.stopPropagation();
    try {
      const item = await patchGalleryImage(image.id, { favorite: !image.favorite });
      if (active?.id === item.id) setActive(item);
      setImages((previous) => previous.map((row) => (row.id === item.id ? item : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Favorite update failed");
    }
  };

  const runOcr = async () => {
    if (!active) return;
    setBusy(true);
    setError(null);
    try {
      const result = await ocrGalleryImage(active.id);
      setActive(result.item);
      setStatus(result.text ? `OCR via ${result.engine}` : "OCR finished with empty text");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "OCR failed");
    } finally {
      setBusy(false);
    }
  };

  const importDocs = async () => {
    if (!active) return;
    setBusy(true);
    setError(null);
    try {
      const result = await importGalleryImageToDocuments(active.id);
      setActive(result.item);
      setStatus(`Imported OCR text as "${result.document.title}"`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  const editorStyle = {
    filter: `brightness(${brightness}%) contrast(${contrast}%)`,
    transform: `rotate(${rotation}deg)`,
    maxWidth: "100%",
    maxHeight: "48vh",
    transition: "filter 0.15s ease",
  };

  return (
    <Box>
      <PageHeader
        title="Gallery"
        description="Media library for uploads and generated images, with search, folders, favorites, and OCR."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Gallery" },
        ]}
        actions={
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(e) => handleFiles(e.target.files)}
            />
            <Button variant="outlined" component="a" href="/documents">
              Documents
            </Button>
            <Button
              variant="outlined"
              color="error"
              disabled={busy || selected.size === 0}
              onClick={() => void handleBulkDelete()}
            >
              Delete selected ({selected.size})
            </Button>
            <Button variant="contained" disabled={uploading} onClick={() => fileInputRef.current?.click()}>
              {uploading ? "Uploading..." : "Upload image"}
            </Button>
          </>
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {status && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setStatus(null)}>
          {status}
        </Alert>
      )}

      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }}>
        <TextField
          size="small"
          label="Search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Title, tags, OCR text, prompt..."
          fullWidth
        />
        <TextField
          size="small"
          label="Folder filter"
          value={folderFilter}
          onChange={(event) => setFolderFilter(event.target.value)}
          placeholder="e.g. screenshots"
          sx={{ minWidth: 180 }}
        />
        <FormControlLabel
          control={<Switch checked={favoritesOnly} onChange={(_, v) => setFavoritesOnly(v)} />}
          label="Favorites"
        />
      </Stack>

      {folders.length > 0 && (
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
          <Chip
            label="All folders"
            color={!folderFilter ? "primary" : "default"}
            onClick={() => setFolderFilter("")}
            size="small"
          />
          {folders.map((name) => (
            <Chip
              key={name}
              label={name}
              color={folderFilter === name ? "primary" : "default"}
              onClick={() => setFolderFilter(name)}
              size="small"
            />
          ))}
        </Stack>
      )}

      <Box
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          void handleFiles(e.dataTransfer.files);
        }}
        sx={{
          border: "2px dashed",
          borderColor: dragOver ? "primary.main" : "divider",
          borderRadius: 2,
          p: 2.5,
          textAlign: "center",
          mb: 3,
          bgcolor: dragOver ? "action.hover" : "transparent",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          Drop images to upload{folderFilter ? ` into folder "${folderFilter}"` : ""}
        </Typography>
      </Box>

      {loading ? (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)", lg: "repeat(4, 1fr)" },
            gap: 2,
          }}
        >
          {Array.from({ length: 8 }).map((_, index) => (
            <SkeletonBlock key={index} height={180} sx={{ aspectRatio: "1" }} />
          ))}
        </Box>
      ) : images.length === 0 ? (
        <EmptyState
          title="No images yet"
          description="Drag and drop images here, upload from your device, or generate assets in chat and review them here."
          icon={<ImageIcon sx={{ fontSize: 48 }} />}
        />
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)", lg: "repeat(4, 1fr)" },
            gap: 2,
          }}
        >
          {images.map((image) => (
            <Box
              key={image.id}
              sx={{
                position: "relative",
                borderRadius: 1,
                overflow: "hidden",
                border: 1,
                borderColor: selected.has(image.id) ? "primary.main" : "divider",
                cursor: "pointer",
                aspectRatio: "1",
              }}
              onClick={() => openEditor(image)}
            >
              <Box
                component="img"
                src={previewUrls[image.id] || undefined}
                alt={image.title || image.filename}
                sx={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  bgcolor: "action.hover",
                }}
              />
              {!previewUrls[image.id] ? (
                <Box
                  sx={{
                    position: "absolute",
                    inset: 0,
                    display: "grid",
                    placeItems: "center",
                    color: "text.secondary",
                    pointerEvents: "none",
                  }}
                >
                  <ImageIcon />
                </Box>
              ) : null}
              <Box
                sx={{
                  position: "absolute",
                  inset: 0,
                  background: "linear-gradient(to top, rgba(0,0,0,0.55), transparent 45%)",
                  pointerEvents: "none",
                }}
              />
              <Checkbox
                size="small"
                checked={selected.has(image.id)}
                onClick={(event) => event.stopPropagation()}
                onChange={() => toggleSelect(image.id)}
                sx={{ position: "absolute", top: 2, left: 2, bgcolor: "background.paper", borderRadius: 1 }}
              />
              <IconButton
                size="small"
                sx={{ position: "absolute", top: 4, right: 40, bgcolor: "background.paper" }}
                onClick={(event) => void toggleFavorite(image, event)}
              >
                {image.favorite ? <FavoriteIcon fontSize="small" color="error" /> : <FavoriteBorderIcon fontSize="small" />}
              </IconButton>
              <IconButton
                size="small"
                sx={{ position: "absolute", top: 4, right: 4, bgcolor: "background.paper" }}
                onClick={(e) => {
                  e.stopPropagation();
                  void handleDelete(image.id);
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
              <Box sx={{ position: "absolute", left: 8, right: 8, bottom: 8 }}>
                <Typography variant="caption" sx={{ color: "#fff", fontWeight: 600 }} noWrap>
                  {image.title || image.original_name || image.filename}
                </Typography>
                <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                  {image.folder ? <Chip size="small" label={image.folder} sx={{ height: 20 }} /> : null}
                  {image.ocr_text ? <Chip size="small" icon={<TextSnippetOutlinedIcon />} label="OCR" sx={{ height: 20 }} /> : null}
                  {image.generation?.prompt ? <Chip size="small" icon={<StarIcon />} label="Gen" sx={{ height: 20 }} /> : null}
                </Stack>
              </Box>
            </Box>
          ))}
        </Box>
      )}

      <Dialog open={editorOpen} onClose={() => setEditorOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{active?.title || active?.filename || "Image"}</DialogTitle>
        <DialogContent>
          {active && (
            <Stack spacing={2}>
              <Box sx={{ textAlign: "center" }}>
                {activePreview ? (
                  <Box component="img" src={activePreview} alt={active.filename} sx={editorStyle} />
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Loading preview...
                  </Typography>
                )}
              </Box>
              <Typography variant="caption" color="text.secondary">
                {humanSize(active.size_bytes)}
                {active.created_at ? ` · ${new Date(active.created_at).toLocaleString()}` : ""}
                {active.ocr_engine ? ` · OCR: ${active.ocr_engine}` : ""}
              </Typography>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <TextField
                  label="Title"
                  size="small"
                  fullWidth
                  value={draftTitle}
                  onChange={(event) => setDraftTitle(event.target.value)}
                />
                <TextField
                  label="Folder"
                  size="small"
                  fullWidth
                  value={draftFolder}
                  onChange={(event) => setDraftFolder(event.target.value)}
                />
              </Stack>
              <TextField
                label="Tags"
                size="small"
                fullWidth
                helperText="Comma-separated"
                value={draftTags}
                onChange={(event) => setDraftTags(event.target.value)}
              />

              {active.generation ? (
                <Alert severity="info">
                  <Typography variant="subtitle2" fontWeight={700}>
                    Generation metadata
                  </Typography>
                  {active.generation.model ? (
                    <Typography variant="body2">Model: {String(active.generation.model)}</Typography>
                  ) : null}
                  {active.generation.source ? (
                    <Typography variant="body2">Source: {String(active.generation.source)}</Typography>
                  ) : null}
                  {active.generation.prompt ? (
                    <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                      Prompt: {String(active.generation.prompt)}
                    </Typography>
                  ) : null}
                </Alert>
              ) : null}

              <Divider />

              <Typography variant="subtitle2" fontWeight={700}>
                OCR text
              </Typography>
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1.5,
                  borderRadius: 1,
                  bgcolor: "action.hover",
                  maxHeight: 180,
                  overflow: "auto",
                  whiteSpace: "pre-wrap",
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                  fontSize: "0.85rem",
                }}
              >
                {active.ocr_text || "No OCR text yet. Run Extract text to read this image."}
              </Box>

              <Typography variant="caption" gutterBottom>
                Brightness ({brightness}%)
              </Typography>
              <Box
                component="input"
                type="range"
                min={50}
                max={150}
                value={brightness}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setBrightness(Number(event.target.value))
                }
                sx={{ width: "100%" }}
              />
              <Typography variant="caption" gutterBottom>
                Contrast ({contrast}%)
              </Typography>
              <Box
                component="input"
                type="range"
                min={50}
                max={150}
                value={contrast}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setContrast(Number(event.target.value))
                }
                sx={{ width: "100%" }}
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions sx={{ flexWrap: "wrap", gap: 1 }}>
          <Button startIcon={<RotateRightIcon />} onClick={() => setRotation((r) => r + 90)}>
            Rotate
          </Button>
          <Button startIcon={<TextSnippetOutlinedIcon />} disabled={busy} onClick={() => void runOcr()}>
            Extract text (OCR)
          </Button>
          <Button
            startIcon={<DescriptionOutlinedIcon />}
            disabled={busy}
            onClick={() => void importDocs()}
          >
            Open in Documents
          </Button>
          <Button disabled={busy} onClick={() => void saveMeta()}>
            Save details
          </Button>
          {active && activePreview && (
            <Button
              startIcon={<DownloadIcon />}
              component="a"
              href={activePreview}
              download={active.original_name || active.filename}
            >
              Download
            </Button>
          )}
          <Button onClick={() => setEditorOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

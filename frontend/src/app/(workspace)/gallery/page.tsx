"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import ImageIcon from "@mui/icons-material/Image";
import RotateRightIcon from "@mui/icons-material/RotateRight";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonBlock } from "@/components/ui/loading";
import {
  deleteGalleryImage,
  fetchGalleryImages,
  galleryImageUrl,
  uploadGalleryImage,
  type GalleryImage,
} from "@/lib/gallery-api";

export default function GalleryPage() {
  const [images, setImages] = React.useState<GalleryImage[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [active, setActive] = React.useState<GalleryImage | null>(null);
  const [brightness, setBrightness] = React.useState(100);
  const [contrast, setContrast] = React.useState(100);
  const [rotation, setRotation] = React.useState(0);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setImages(await fetchGalleryImages());
    } catch {
      setImages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) {
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const uploaded: GalleryImage[] = [];
      for (const file of Array.from(files)) {
        if (!file.type.startsWith("image/")) {
          continue;
        }
        uploaded.push(await uploadGalleryImage(file));
      }
      setImages((prev) => [...uploaded, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const openEditor = (image: GalleryImage) => {
    setActive(image);
    setBrightness(100);
    setContrast(100);
    setRotation(0);
    setEditorOpen(true);
  };

  const handleDelete = async (imageId: string) => {
    setError(null);
    try {
      await deleteGalleryImage(imageId);
      setImages((prev) => prev.filter((img) => img.id !== imageId));
      if (active?.id === imageId) {
        setEditorOpen(false);
        setActive(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const editorStyle = {
    filter: `brightness(${brightness}%) contrast(${contrast}%)`,
    transform: `rotate(${rotation}deg)`,
    maxWidth: "100%",
    maxHeight: "60vh",
    transition: "filter 0.15s ease",
  };

  return (
    <Box>
      <PageHeader
        title="Gallery"
        description="Review generated and uploaded images."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
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
            <Button variant="contained" disabled={uploading} onClick={() => fileInputRef.current?.click()}>
              {uploading ? "Uploading..." : "Upload image"}
            </Button>
          </>
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
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
          handleFiles(e.dataTransfer.files);
        }}
        sx={{
          border: "2px dashed",
          borderColor: dragOver ? "primary.main" : "divider",
          borderRadius: 2,
          p: 3,
          textAlign: "center",
          mb: 3,
          bgcolor: dragOver ? "action.hover" : "transparent",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          Drop images to upload
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
          description="Drag and drop images here or upload from your device."
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
                borderColor: "divider",
                cursor: "pointer",
                aspectRatio: "1",
              }}
              onClick={() => openEditor(image)}
            >
              <Box
                component="img"
                src={galleryImageUrl(image)}
                alt={image.filename}
                sx={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
              <IconButton
                size="small"
                sx={{ position: "absolute", top: 4, right: 4, bgcolor: "background.paper" }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(image.id);
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
        </Box>
      )}

      <Dialog open={editorOpen} onClose={() => setEditorOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{active?.filename || "Image editor"}</DialogTitle>
        <DialogContent>
          {active && (
            <Box sx={{ textAlign: "center", mb: 3 }}>
              <Box component="img" src={galleryImageUrl(active)} alt={active.filename} sx={editorStyle} />
            </Box>
          )}
          <Typography variant="caption" gutterBottom>
            Brightness
          </Typography>
          <Slider value={brightness} min={50} max={150} onChange={(_e, v) => setBrightness(v as number)} />
          <Typography variant="caption" gutterBottom>
            Contrast
          </Typography>
          <Slider value={contrast} min={50} max={150} onChange={(_e, v) => setContrast(v as number)} />
        </DialogContent>
        <DialogActions>
          <Button startIcon={<RotateRightIcon />} onClick={() => setRotation((r) => r + 90)}>
            Rotate
          </Button>
          {active && (
            <Button
              startIcon={<DownloadIcon />}
              component="a"
              href={galleryImageUrl(active)}
              download={active.filename}
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

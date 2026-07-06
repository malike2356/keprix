"use client";

import { IconCloudUpload, IconTrash } from "@tabler/icons-react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Drawer from "@mui/material/Drawer";
import Grid from "@mui/material/Grid2";
import LinearProgress from "@mui/material/LinearProgress";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import PageContainer from "@/components/shared/PageContainer";
import EmptyState from "@/components/ui/EmptyState";
import {
  deleteMemoryDocument,
  fetchMemoryDocument,
  fetchMemoryDocuments,
  formatBytes,
  indexMemoryUrl,
  uploadMemoryDocument,
  type MemoryDocument,
} from "@/lib/admin-workspace-api";
import { formatTimeAgo } from "@/lib/time-ago";

export default function AdminMemoryPage() {
  const [search, setSearch] = React.useState("");
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [uploadTab, setUploadTab] = React.useState(0);
  const [url, setUrl] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [preview, setPreview] = React.useState<MemoryDocument | null>(null);

  const { data, isLoading, mutate } = useSWR(["admin-memory", search], () => fetchMemoryDocuments(search));

  const onUploadFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        await uploadMemoryDocument(file);
      }
      setUploadOpen(false);
      await mutate();
    } finally {
      setBusy(false);
    }
  };

  const onIndexUrl = async () => {
    if (!url.trim()) return;
    setBusy(true);
    try {
      await indexMemoryUrl(url.trim());
      setUploadOpen(false);
      setUrl("");
      await mutate();
    } finally {
      setBusy(false);
    }
  };

  const openPreview = async (doc: MemoryDocument) => {
    const detail = await fetchMemoryDocument(doc.id);
    setPreview(detail);
  };

  return (
    <PageContainer title="Memory Store" description="RAG documents and vector index." padded={false}>
      <Box sx={{ display: "grid", gap: 2 }}>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <TextField
            size="small"
            placeholder="Search documents..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            sx={{ minWidth: 260 }}
          />
          <Button variant="contained" onClick={() => setUploadOpen(true)}>
            Upload document
          </Button>
        </Box>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <DashboardCard title="Total documents" middleContent={<Typography variant="h4">{data?.stats.total_documents ?? 0}</Typography>} />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <DashboardCard title="Total chunks indexed" middleContent={<Typography variant="h4">{data?.stats.total_chunks ?? 0}</Typography>} />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <DashboardCard
              title="Last indexed"
              middleContent={<Typography variant="h6">{formatTimeAgo(data?.stats.last_indexed_at) || "Never"}</Typography>}
            />
          </Grid>
        </Grid>

        <DashboardCard title="Documents">
          {isLoading ? (
            <LinearProgress />
          ) : !data?.items.length ? (
            <EmptyState
              title="No documents indexed"
              description="Upload a file or index a URL to populate the memory store."
              icon={<IconCloudUpload size={48} stroke={1.5} />}
            />
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Chunks</TableCell>
                  <TableCell>Uploaded</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.items.map((doc) => (
                  <TableRow key={doc.id} hover onClick={() => void openPreview(doc)} sx={{ cursor: "pointer" }}>
                    <TableCell>{doc.name}</TableCell>
                    <TableCell>
                      <Chip size="small" label={doc.type} />
                    </TableCell>
                    <TableCell>{formatBytes(doc.size_bytes)}</TableCell>
                    <TableCell>{doc.chunks}</TableCell>
                    <TableCell>
                      {formatTimeAgo(doc.uploaded_at)}
                      {doc.uploaded_by ? ` by ${doc.uploaded_by}` : ""}
                    </TableCell>
                    <TableCell>
                      <Chip size="small" color={doc.status === "indexed" ? "success" : "warning"} label={doc.status} />
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        color="error"
                        startIcon={<IconTrash size={16} stroke={1.75} />}
                        onClick={(event) => {
                          event.stopPropagation();
                          void deleteMemoryDocument(doc.id).then(() => mutate());
                        }}
                      >
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DashboardCard>
      </Box>

      <Dialog open={uploadOpen} onClose={() => setUploadOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload document</DialogTitle>
        <DialogContent>
          <Tabs value={uploadTab} onChange={(_, value) => setUploadTab(value)} sx={{ mb: 2 }}>
            <Tab label="File upload" />
            <Tab label="Index URL" />
          </Tabs>
          {uploadTab === 0 ? (
            <Box
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                void onUploadFiles(event.dataTransfer.files);
              }}
              sx={{
                border: "2px dashed",
                borderColor: "divider",
                borderRadius: 2,
                p: 4,
                textAlign: "center",
              }}
            >
              <IconCloudUpload size={40} stroke={1.5} style={{ marginBottom: 8 }} />
              <Typography variant="body2" sx={{ mb: 2 }}>
                Drag and drop PDF, Markdown, TXT, or DOCX files here.
              </Typography>
              <Button component="label" variant="outlined">
                Choose files
                <input
                  hidden
                  type="file"
                  accept=".pdf,.md,.txt,.docx"
                  multiple
                  onChange={(event) => void onUploadFiles(event.target.files)}
                />
              </Button>
            </Box>
          ) : (
            <TextField
              fullWidth
              label="Web page URL"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com/docs"
            />
          )}
          {busy ? <LinearProgress sx={{ mt: 2 }} /> : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadOpen(false)}>Cancel</Button>
          {uploadTab === 1 ? (
            <Button variant="contained" disabled={busy || !url.trim()} onClick={() => void onIndexUrl()}>
              Index URL
            </Button>
          ) : null}
        </DialogActions>
      </Dialog>

      <Drawer anchor="right" open={Boolean(preview)} onClose={() => setPreview(null)} PaperProps={{ sx: { width: 480 } }}>
        <Box sx={{ p: 3 }}>
          <Typography variant="h6">{preview?.name}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {preview?.type} | {formatBytes(preview?.size_bytes || 0)} | {preview?.chunks} chunks
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {preview?.preview || "No preview available."}
          </Typography>
        </Box>
      </Drawer>
    </PageContainer>
  );
}

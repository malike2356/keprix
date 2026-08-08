"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  addWorkerKbEntry,
  deleteWorkerKbEntry,
  fetchWorkerKbEntries,
  searchWorkerKb,
  toggleWorkerKbEntry,
} from "@/lib/worker-kb-api";

export default function WorkerKbPage() {
  const workspaceId = "default";
  const [workerId, setWorkerId] = React.useState("default-worker");
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [entryType, setEntryType] = React.useState("faq");
  const [query, setQuery] = React.useState("");
  const [searchHits, setSearchHits] = React.useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const entries = useSWR(["worker-kb", workspaceId, workerId], () =>
    fetchWorkerKbEntries(workerId, workspaceId),
  );

  const onAdd = async () => {
    setBusy(true);
    setError(null);
    try {
      await addWorkerKbEntry({
        workerId,
        content: content.trim(),
        title: title.trim() || undefined,
        entryType,
        workspaceId,
      });
      setContent("");
      setTitle("");
      await entries.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Add failed");
    } finally {
      setBusy(false);
    }
  };

  const onSearch = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await searchWorkerKb(workerId, query.trim(), workspaceId);
      setSearchHits(result.results || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Worker knowledge base"
        description="Per-worker FAQs, documents, and instructions injected into agent runs. Available in standalone Keprix without Aiva UI."
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
        <TextField
          size="small"
          label="Worker ID"
          value={workerId}
          onChange={(e) => setWorkerId(e.target.value)}
          sx={{ minWidth: 220 }}
        />
        <Button size="small" variant="outlined" onClick={() => void entries.mutate()}>
          Refresh
        </Button>
      </Stack>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Add entry
          </Typography>
          <Stack spacing={1}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <TextField
                size="small"
                fullWidth
                label="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <TextField
                size="small"
                select
                label="Type"
                value={entryType}
                onChange={(e) => setEntryType(e.target.value)}
                sx={{ minWidth: 140 }}
              >
                <MenuItem value="faq">FAQ</MenuItem>
                <MenuItem value="document">Document</MenuItem>
                <MenuItem value="instruction">Instruction</MenuItem>
              </TextField>
            </Stack>
            <TextField
              size="small"
              fullWidth
              multiline
              minRows={3}
              label="Content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
            <Button
              variant="contained"
              disabled={busy || !content.trim() || !workerId.trim()}
              onClick={() => void onAdd()}
              sx={{ alignSelf: "flex-start" }}
            >
              Add to KB
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Search
          </Typography>
          <Stack direction="row" spacing={1}>
            <TextField
              size="small"
              fullWidth
              label="Query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <Button variant="outlined" disabled={busy || !query.trim()} onClick={() => void onSearch()}>
              Search
            </Button>
          </Stack>
          {searchHits.length > 0 ? (
            <Box sx={{ mt: 1, p: 1.5, bgcolor: "action.hover", overflow: "auto" }}>
              <StructuredDataView value={searchHits} />
            </Box>
          ) : null}
        </CardContent>
      </Card>

      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Entries ({entries.data?.count ?? 0})
      </Typography>
      <Stack spacing={1}>
        {(entries.data?.entries ?? []).map((entry) => {
          const enabled = Boolean(entry.enabled);
          return (
            <Card key={entry.id} variant="outlined">
              <CardContent>
                <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
                  <Box>
                    <Typography variant="subtitle2">
                      {entry.title || "(untitled)"} · {entry.entry_type} · {enabled ? "on" : "off"}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {(entry.content || "").slice(0, 240)}
                      {(entry.content || "").length > 240 ? "…" : ""}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={busy}
                      onClick={() =>
                        void toggleWorkerKbEntry(entry.id, workerId, !enabled, workspaceId).then(() =>
                          entries.mutate(),
                        )
                      }
                    >
                      {enabled ? "Disable" : "Enable"}
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      disabled={busy}
                      onClick={() =>
                        void deleteWorkerKbEntry(entry.id, workerId, workspaceId).then(() => entries.mutate())
                      }
                    >
                      Delete
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          );
        })}
        {!entries.isLoading && (entries.data?.entries?.length ?? 0) === 0 ? (
          <Alert severity="info">No entries for this worker yet.</Alert>
        ) : null}
      </Stack>
    </Box>
  );
}

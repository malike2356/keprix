"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import InputBase from "@mui/material/InputBase";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import {
  fetchSelfKnowledgeStatus,
  searchSelfKnowledge,
  triggerIngest,
  triggerIngestAndWait,
  type IngestResult,
  type SearchResponse,
} from "@/lib/self-knowledge-api";

export default function SelfKnowledgePage() {
  const { data: status, error, isLoading, mutate } = useSWR(
    "self-knowledge-status",
    fetchSelfKnowledgeStatus,
    { refreshInterval: 0 }
  );

  const [ingestState, setIngestState] = React.useState<
    "idle" | "running" | "done" | "error"
  >("idle");
  const [ingestResult, setIngestResult] = React.useState<IngestResult | null>(null);
  const [ingestError, setIngestError] = React.useState<string | null>(null);

  const [query, setQuery] = React.useState("");
  const [searchResult, setSearchResult] = React.useState<SearchResponse | null>(null);
  const [searching, setSearching] = React.useState(false);

  const handleIngest = async (mode: "fast" | "full") => {
    setIngestState("running");
    setIngestResult(null);
    setIngestError(null);
    try {
      if (mode === "fast") {
        const result = await triggerIngestAndWait({
          includeCodebase: false,
          includeDocs: true,
          maxFiles: 500,
        });
        setIngestResult(result);
        setIngestState("done");
      } else {
        await triggerIngest({ includeCodbase: true, includeDocs: true });
        setIngestState("done");
        setIngestResult(null);
      }
      await mutate();
    } catch (e) {
      setIngestError(String(e));
      setIngestState("error");
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearchResult(null);
    try {
      const res = await searchSelfKnowledge(query.trim(), 8);
      setSearchResult(res);
    } catch {
      // ignore
    } finally {
      setSearching(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", py: 4, px: 2 }}>
      <PageHeader
        title="Self-Knowledge"
        description="Keprix knows its own codebase and capabilities via a live RAG index. Rebuild it here after major changes."
      />

      {isLoading && <SkeletonList rows={3} />}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load status: {String(error)}
        </Alert>
      )}

      {status && (
        <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
            <Chip
              label={status.indexed ? "Indexed" : "Not indexed"}
              color={status.indexed ? "success" : "default"}
              size="small"
            />
            {status.indexed && (
              <>
                <Typography variant="body2" color="text.secondary">
                  {status.document_count} documents
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {status.total_chunks} chunks
                </Typography>
              </>
            )}
            {status.error && (
              <Typography variant="body2" color="error">
                {status.error}
              </Typography>
            )}
          </Stack>
        </Paper>
      )}

      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Re-index self-knowledge
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Fast index: synthetic reference docs and curated markdown only (30 seconds).
          Full index: adds the entire codebase (5-10 minutes, runs in background).
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            size="small"
            disabled={ingestState === "running"}
            onClick={() => handleIngest("fast")}
            startIcon={ingestState === "running" ? <CircularProgress size={14} /> : undefined}
          >
            {ingestState === "running" ? "Indexing..." : "Fast index (wait)"}
          </Button>
          <Button
            variant="outlined"
            size="small"
            disabled={ingestState === "running"}
            onClick={() => handleIngest("full")}
          >
            Full index (background)
          </Button>
        </Stack>

        {ingestState === "done" && ingestResult && (
          <Alert severity="success" sx={{ mt: 2 }}>
            Indexed {ingestResult.synthetic_docs} synthetic docs ({ingestResult.synthetic_chunks} chunks).
            Total chunks: {ingestResult.total_chunks}.
            {ingestResult.errors.length > 0 && (
              <> {ingestResult.errors.length} error(s): {ingestResult.errors.join("; ")}</>
            )}
          </Alert>
        )}
        {ingestState === "done" && !ingestResult && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Full indexing started in background. Check logs for progress.
          </Alert>
        )}
        {ingestState === "error" && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {ingestError}
          </Alert>
        )}
      </Paper>

      <Divider sx={{ mb: 3 }} />

      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Test retrieval
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Search the self-knowledge index to verify what Keprix knows about a topic.
        </Typography>
        <Box
          component="form"
          onSubmit={handleSearch}
          sx={{ display: "flex", gap: 1, mb: 2 }}
        >
          <InputBase
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. feature flags, billing, API routes, voice..."
            sx={{
              flex: 1,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 1,
              px: 1.5,
              py: 0.5,
            }}
          />
          <Button type="submit" variant="outlined" size="small" disabled={searching}>
            {searching ? <CircularProgress size={14} /> : "Search"}
          </Button>
        </Box>

        {searchResult && (
          <Box>
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              {searchResult.results.length} results for "{searchResult.query}"
            </Typography>
            {searchResult.results.slice(0, 5).map((r, i) => (
              <Paper
                key={i}
                variant="outlined"
                sx={{ p: 1.5, mb: 1, bgcolor: "background.default" }}
              >
                <Stack direction="row" spacing={1} alignItems="center" mb={0.5}>
                  <Chip label={r.source} size="small" variant="outlined" />
                  {r.score !== undefined && (
                    <Typography variant="caption" color="text.secondary">
                      score: {r.score.toFixed(3)}
                    </Typography>
                  )}
                </Stack>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: "pre-wrap",
                    fontFamily: "monospace",
                    fontSize: "0.72rem",
                    maxHeight: 160,
                    overflow: "hidden",
                    color: "text.secondary",
                  }}
                >
                  {r.content.slice(0, 600)}
                  {r.content.length > 600 ? "..." : ""}
                </Typography>
              </Paper>
            ))}
          </Box>
        )}
      </Paper>

      {status?.sources && status.sources.length > 0 && (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Indexed documents ({status.sources.length})
          </Typography>
          <Stack spacing={0.5}>
            {status.sources.map((s) => (
              <Stack
                key={s.source_id}
                direction="row"
                spacing={2}
                alignItems="center"
              >
                <Typography
                  variant="body2"
                  sx={{ flex: 1, fontFamily: "monospace", fontSize: "0.75rem" }}
                >
                  {s.source_id}
                </Typography>
                <Chip
                  label={`${s.chunk_count} chunks`}
                  size="small"
                  variant="outlined"
                />
              </Stack>
            ))}
          </Stack>
        </Paper>
      )}
    </Box>
  );
}

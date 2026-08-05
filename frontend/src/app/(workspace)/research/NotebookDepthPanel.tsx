"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  exportNotebookResearch,
  fetchNotebookResearchConfig,
  normalizeNotebookSource,
  sendNotebookReportToGraph,
  startNotebookResearch,
  type NotebookResearchConfig,
  type NotebookResearchDepth,
  type NotebookResearchJob,
  type NotebookSource,
} from "@/lib/research-api";

export default function NotebookDepthPanel() {
  const [config, setConfig] = React.useState<NotebookResearchConfig>({
    enabled: false,
    native_max_sources: 20,
    external_enabled: false,
    graph_ingest_enabled: false,
  });
  const [depth, setDepth] = React.useState<NotebookResearchDepth>("notebook");
  const [query, setQuery] = React.useState("");
  const [sourceText, setSourceText] = React.useState("");
  const [sourceTitle, setSourceTitle] = React.useState("");
  const [sourceUrl, setSourceUrl] = React.useState("");
  const [sources, setSources] = React.useState<NotebookSource[]>([]);
  const [job, setJob] = React.useState<NotebookResearchJob | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetchNotebookResearchConfig().then(setConfig).catch(() => undefined);
  }, []);

  const addSource = async (source: Omit<NotebookSource, "id">) => {
    setError(null);
    try {
      const normalized = await normalizeNotebookSource(source);
      setSources((current) => [...current, normalized]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add source");
    }
  };

  const addTextSource = async () => {
    if (!sourceText.trim()) {
      return;
    }
    await addSource({
      kind: "text",
      ref: sourceText.trim(),
      title: sourceTitle.trim() || `Source ${sources.length + 1}`,
      excerpt: sourceText.trim(),
    });
    setSourceText("");
    setSourceTitle("");
  };

  const addUrlSource = async () => {
    if (!sourceUrl.trim()) {
      return;
    }
    await addSource({ kind: "url", ref: sourceUrl.trim(), title: sourceUrl.trim(), excerpt: sourceUrl.trim() });
    setSourceUrl("");
  };

  const addFileSource = async (file: File | undefined) => {
    if (!file) {
      return;
    }
    const text = await file.text();
    await addSource({ kind: "file", ref: file.name, title: file.name, excerpt: text });
  };

  const runNotebook = async () => {
    if (!query.trim() || sources.length < 2 || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const nextJob = await startNotebookResearch(query.trim(), depth, sources);
      setJob(nextJob);
      if (nextJob.error) {
        setMessage(nextJob.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notebook research failed");
    } finally {
      setBusy(false);
    }
  };

  const exportMarkdown = async () => {
    if (!job) {
      return;
    }
    setMessage(null);
    try {
      const result = await exportNotebookResearch(job.job_id);
      setMessage(`Exported Markdown to ${result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notebook export failed");
    }
  };

  const ingestGraph = async () => {
    if (!job) {
      return;
    }
    setMessage(null);
    try {
      await sendNotebookReportToGraph(job);
      setMessage("Sent notebook report to graph ingest.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Graph ingest failed");
    }
  };

  if (!config.enabled) {
    return null;
  }

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Stack spacing={2}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "flex-end" }}>
            <TextField
              label="Notebook question"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              fullWidth
              multiline
              minRows={2}
            />
            <FormControl size="small" sx={{ minWidth: 190 }}>
              <InputLabel id="notebook-depth-label">Notebook depth</InputLabel>
              <Select
                labelId="notebook-depth-label"
                label="Notebook depth"
                value={depth}
                onChange={(event) => setDepth(event.target.value as NotebookResearchDepth)}
              >
                <MenuItem value="notebook">Quick Notebook</MenuItem>
                {config.external_enabled ? <MenuItem value="notebook-external">External</MenuItem> : null}
              </Select>
            </FormControl>
            <Button variant="contained" disabled={!query.trim() || sources.length < 2 || busy} onClick={runNotebook}>
              {busy ? "Running..." : "Run notebook"}
            </Button>
          </Stack>

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField
              label="Source title"
              value={sourceTitle}
              onChange={(event) => setSourceTitle(event.target.value)}
              size="small"
              sx={{ minWidth: { md: 180 } }}
            />
            <TextField
              label="Paste source text"
              value={sourceText}
              onChange={(event) => setSourceText(event.target.value)}
              fullWidth
              multiline
              minRows={2}
            />
            <Button variant="outlined" disabled={!sourceText.trim()} onClick={() => void addTextSource()}>
              Add text
            </Button>
          </Stack>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <TextField
              label="Add URL"
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              size="small"
              fullWidth
            />
            <Button variant="outlined" disabled={!sourceUrl.trim()} onClick={() => void addUrlSource()}>
              Add URL
            </Button>
            <Button variant="outlined" component="label">
              Upload txt/PDF
              <input hidden type="file" accept=".txt,.md,.pdf,text/*,application/pdf" onChange={(event) => void addFileSource(event.target.files?.[0])} />
            </Button>
          </Stack>

          {sources.length ? (
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              {sources.map((source, index) => (
                <Chip
                  key={source.id || `${source.kind}-${index}`}
                  label={`${index + 1}. ${source.title || source.kind}`}
                  onDelete={() => setSources((current) => current.filter((_, sourceIndex) => sourceIndex !== index))}
                />
              ))}
            </Stack>
          ) : null}

          {error ? <Alert severity="error">{error}</Alert> : null}
          {message ? <Alert severity="info" onClose={() => setMessage(null)}>{message}</Alert> : null}

          {job?.report_md ? (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 280px" }, gap: 2 }}>
              <Box sx={{ "& h1, & h2, & h3": { mt: 2 }, "& p, & li": { lineHeight: 1.7 } }}>
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 1 }}>
                  <Button size="small" variant="outlined" onClick={() => void exportMarkdown()}>
                    Export Markdown
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={!config.graph_ingest_enabled}
                    onClick={() => void ingestGraph()}
                  >
                    Send to graph ingest
                  </Button>
                </Stack>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{job.report_md}</ReactMarkdown>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  Citations
                </Typography>
                <List dense disablePadding>
                  {job.citations.map((citation, index) => (
                    <ListItem key={`${citation.id || index}`} disablePadding sx={{ mb: 1 }}>
                      <ListItemText
                        primary={`${citation.id || `S${index + 1}`} ${citation.title || ""}`}
                        secondary={String(citation.excerpt || citation.ref || "")}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            </Box>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

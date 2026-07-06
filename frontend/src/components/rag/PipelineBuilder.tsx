"use client";

import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  ingestNotionPipeline,
  ingestPipelineDocument,
  listPipelineStores,
} from "@/lib/rag-pipeline-api";

type SourceType = "manual" | "notion";

type Props = {
  pipelineId: string;
  onPipelineIdChange: (value: string) => void;
  onIngested?: () => void;
  initialSourceType?: SourceType;
};

function parseIdList(raw: string): string[] {
  return raw
    .split(/[,\n]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

export default function PipelineBuilder({
  pipelineId,
  onPipelineIdChange,
  onIngested,
  initialSourceType = "manual",
}: Props) {
  const [sourceType, setSourceType] = React.useState<SourceType>(initialSourceType);
  const [sourceId, setSourceId] = React.useState("handbook");
  const [content, setContent] = React.useState(
    "Building 3 maintenance schedule covers HVAC checks every Monday.",
  );
  const [notionPageIds, setNotionPageIds] = React.useState("");
  const [notionDatabaseIds, setNotionDatabaseIds] = React.useState("");
  const [notionToken, setNotionToken] = React.useState("");
  const [storeKind, setStoreKind] = React.useState("memory");
  const [stores, setStores] = React.useState<Array<Record<string, string>>>([]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    setSourceType(initialSourceType);
  }, [initialSourceType]);

  React.useEffect(() => {
    listPipelineStores()
      .then((payload) => setStores(payload.stores || []))
      .catch(() => setStores([{ kind: "memory", description: "In-memory test store" }]));
  }, []);

  const onIngest = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await ingestPipelineDocument({
        pipeline_id: pipelineId,
        source_id: sourceId,
        content,
        store_kind: storeKind,
      });
      setMessage(`Ingested ${result.run_id} (${result.trace?.length || 0} trace steps)`);
      onIngested?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setBusy(false);
    }
  };

  const onIngestNotion = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await ingestNotionPipeline({
        pipeline_id: pipelineId,
        store_kind: storeKind,
        page_ids: parseIdList(notionPageIds),
        database_ids: parseIdList(notionDatabaseIds),
        token: notionToken.trim() || undefined,
      });
      setMessage(
        `Ingested ${result.documents_ingested} Notion document(s); last run ${result.run_id}`,
      );
      onIngested?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notion ingest failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Pipeline builder
        </Typography>
        <Box sx={{ display: "grid", gap: 2 }}>
          <TextField
            label="Pipeline ID"
            value={pipelineId}
            onChange={(e) => onPipelineIdChange(e.target.value)}
            size="small"
          />
          <TextField
            select
            label="Source type"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
            size="small"
          >
            <MenuItem value="manual">Manual text</MenuItem>
            <MenuItem value="notion">Notion</MenuItem>
          </TextField>
          <TextField
            select
            label="Document store"
            value={storeKind}
            onChange={(e) => setStoreKind(e.target.value)}
            size="small"
          >
            {(stores.length ? stores : [{ kind: "memory" }]).map((store) => (
              <MenuItem key={store.kind} value={store.kind}>
                {store.kind}
                {store.description ? ` - ${store.description}` : ""}
              </MenuItem>
            ))}
          </TextField>
          {sourceType === "manual" ? (
            <>
              <TextField
                label="Source ID"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                size="small"
              />
              <TextField
                label="Document content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                size="small"
                multiline
                minRows={4}
              />
              <Button variant="contained" startIcon={<AddIcon />} onClick={onIngest} disabled={busy}>
                Ingest through pipeline
              </Button>
            </>
          ) : (
            <>
              <TextField
                label="Page IDs"
                value={notionPageIds}
                onChange={(e) => setNotionPageIds(e.target.value)}
                size="small"
                multiline
                minRows={2}
                placeholder="Comma or newline separated Notion page IDs"
                helperText="Optional when database IDs are set; leave blank to search the workspace"
              />
              <TextField
                label="Database IDs"
                value={notionDatabaseIds}
                onChange={(e) => setNotionDatabaseIds(e.target.value)}
                size="small"
                multiline
                minRows={2}
                placeholder="Comma or newline separated data source / database IDs"
              />
              <TextField
                label="Notion token (optional)"
                type="password"
                value={notionToken}
                onChange={(e) => setNotionToken(e.target.value)}
                size="small"
                helperText="Leave blank to use KEPRIX_NOTION_TOKEN or NOTION_TOKEN from the environment"
              />
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={onIngestNotion}
                disabled={busy}
              >
                Ingest from Notion
              </Button>
            </>
          )}
        </Box>
        {error ? (
          <Typography color="error" variant="body2" sx={{ mt: 2 }}>
            {error}
          </Typography>
        ) : null}
        {message ? (
          <Typography variant="body2" sx={{ mt: 2 }}>
            {message}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
}

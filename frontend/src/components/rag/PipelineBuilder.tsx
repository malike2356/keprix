"use client";

import AddIcon from "@mui/icons-material/Add";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  createPipeline,
  ingestNotionPipeline,
  ingestPipelineDocument,
  ingestPipelinePath,
  ingestPipelineUpload,
  ingestPipelineUrl,
  listPipelineStores,
} from "@/lib/rag-pipeline-api";

type SourceType = "manual" | "notion" | "file" | "vault" | "url";

type Props = {
  pipelineId: string;
  onPipelineIdChange: (value: string) => void;
  onIngested?: () => void;
  initialSourceType?: SourceType;
  defaultPipelineId?: string;
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
  defaultPipelineId = "production-default",
}: Props) {
  const [sourceType, setSourceType] = React.useState<SourceType>(initialSourceType);
  const [sourceId, setSourceId] = React.useState("handbook");
  const [content, setContent] = React.useState(
    "Building 3 maintenance schedule covers HVAC checks every Monday.",
  );
  const [notionPageIds, setNotionPageIds] = React.useState("");
  const [notionDatabaseIds, setNotionDatabaseIds] = React.useState("");
  const [notionToken, setNotionToken] = React.useState("");
  const [filePath, setFilePath] = React.useState("");
  const [url, setUrl] = React.useState("");
  const [storeKind, setStoreKind] = React.useState("memory");
  const [stores, setStores] = React.useState<Array<Record<string, string | number>>>([]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const fileRef = React.useRef<HTMLInputElement | null>(null);

  React.useEffect(() => {
    setSourceType(initialSourceType);
  }, [initialSourceType]);

  React.useEffect(() => {
    listPipelineStores()
      .then((payload) => setStores(payload.stores || []))
      .catch(() => setStores([{ kind: "memory", description: "In-memory test store", run_count: 0 }]));
  }, []);

  const finish = (text: string) => {
    setMessage(text);
    onIngested?.();
  };

  const onCreatePipeline = async () => {
    setBusy(true);
    setError(null);
    try {
      await createPipeline(pipelineId, storeKind);
      finish(`Pipeline ${pipelineId} ready (store ${storeKind}).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create pipeline");
    } finally {
      setBusy(false);
    }
  };

  const onIngest = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      if (sourceType === "manual") {
        const result = await ingestPipelineDocument({
          pipeline_id: pipelineId,
          source_id: sourceId,
          content,
          store_kind: storeKind,
        });
        finish(`Ingested ${result.run_id} (${result.trace?.length || 0} trace steps)`);
      } else if (sourceType === "notion") {
        const result = await ingestNotionPipeline({
          pipeline_id: pipelineId,
          store_kind: storeKind,
          page_ids: parseIdList(notionPageIds),
          database_ids: parseIdList(notionDatabaseIds),
          token: notionToken.trim() || undefined,
        });
        finish(`Ingested ${result.documents_ingested} Notion document(s); last run ${result.run_id}`);
      } else if (sourceType === "vault" || sourceType === "file") {
        const result = await ingestPipelinePath({
          path: filePath,
          pipeline_id: pipelineId,
          store_kind: storeKind,
          vault_relative: sourceType === "vault",
        });
        finish(`Ingested path run ${result.run_id}`);
      } else if (sourceType === "url") {
        const result = await ingestPipelineUrl({
          url,
          pipeline_id: pipelineId,
          store_kind: storeKind,
        });
        finish(`Ingested URL run ${result.run_id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setBusy(false);
    }
  };

  const onUpload = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      const result = await ingestPipelineUpload({
        file,
        pipeline_id: pipelineId,
        store_kind: storeKind,
      });
      finish(`Uploaded and ingested ${result.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Pipelines and sources
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Default pipeline id is <strong>{defaultPipelineId}</strong> (env KEPRIX_RAG_DEFAULT_PIPELINE_ID).
        </Typography>
        <Box sx={{ display: "grid", gap: 2 }}>
          <StackFields
            pipelineId={pipelineId}
            onPipelineIdChange={onPipelineIdChange}
            sourceType={sourceType}
            setSourceType={setSourceType}
            storeKind={storeKind}
            setStoreKind={setStoreKind}
            stores={stores}
            onCreatePipeline={onCreatePipeline}
            busy={busy}
          />

          {sourceType === "manual" ? (
            <>
              <TextField label="Source ID" value={sourceId} onChange={(e) => setSourceId(e.target.value)} size="small" />
              <TextField
                label="Document content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                size="small"
                multiline
                minRows={4}
              />
            </>
          ) : null}

          {sourceType === "notion" ? (
            <>
              <TextField
                label="Page IDs"
                value={notionPageIds}
                onChange={(e) => setNotionPageIds(e.target.value)}
                size="small"
                multiline
                minRows={2}
              />
              <TextField
                label="Database IDs"
                value={notionDatabaseIds}
                onChange={(e) => setNotionDatabaseIds(e.target.value)}
                size="small"
                multiline
                minRows={2}
              />
              <TextField
                label="Notion token (optional)"
                type="password"
                value={notionToken}
                onChange={(e) => setNotionToken(e.target.value)}
                size="small"
              />
            </>
          ) : null}

          {sourceType === "file" || sourceType === "vault" ? (
            <TextField
              label={sourceType === "vault" ? "Vault-relative path" : "Absolute local path"}
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              size="small"
              placeholder={sourceType === "vault" ? "notes/handbook.md" : "/data/docs/handbook.md"}
            />
          ) : null}

          {sourceType === "url" ? (
            <TextField label="URL" value={url} onChange={(e) => setUrl(e.target.value)} size="small" />
          ) : null}

          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => void onIngest()} disabled={busy}>
              Ingest
            </Button>
            <Button variant="outlined" disabled={busy} onClick={() => fileRef.current?.click()}>
              Upload text/markdown file
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.markdown,.csv"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void onUpload(file);
                e.target.value = "";
              }}
            />
          </Box>
        </Box>
        {error ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        ) : null}
        {message ? (
          <Alert severity="success" sx={{ mt: 2 }}>
            {message}
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

function StackFields(props: {
  pipelineId: string;
  onPipelineIdChange: (v: string) => void;
  sourceType: SourceType;
  setSourceType: (v: SourceType) => void;
  storeKind: string;
  setStoreKind: (v: string) => void;
  stores: Array<Record<string, string | number>>;
  onCreatePipeline: () => void;
  busy: boolean;
}) {
  return (
    <>
      <TextField
        label="Pipeline ID"
        value={props.pipelineId}
        onChange={(e) => props.onPipelineIdChange(e.target.value)}
        size="small"
        helperText="Create or open a named pipeline id"
      />
      <Button size="small" variant="outlined" disabled={props.busy} onClick={props.onCreatePipeline}>
        Create / open pipeline
      </Button>
      <TextField
        select
        label="Source type"
        value={props.sourceType}
        onChange={(e) => props.setSourceType(e.target.value as SourceType)}
        size="small"
      >
        <MenuItem value="manual">Manual text</MenuItem>
        <MenuItem value="notion">Notion</MenuItem>
        <MenuItem value="file">Local path</MenuItem>
        <MenuItem value="vault">Vault path</MenuItem>
        <MenuItem value="url">URL</MenuItem>
      </TextField>
      <TextField
        select
        label="Document store"
        value={props.storeKind}
        onChange={(e) => props.setStoreKind(e.target.value)}
        size="small"
      >
        {(props.stores.length ? props.stores : [{ kind: "memory" }]).map((store) => (
          <MenuItem key={String(store.kind)} value={String(store.kind)}>
            {String(store.kind)}
            {store.description ? ` - ${store.description}` : ""}
            {store.run_count != null ? ` (${store.run_count} runs)` : ""}
          </MenuItem>
        ))}
      </TextField>
    </>
  );
}

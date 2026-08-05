"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import ComponentInspector from "@/components/design/ComponentInspector";
import PreviewFrame from "@/components/design/PreviewFrame";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type PreviewSession = {
  session_id: string;
  root_path?: string | null;
  artifact_id?: string | null;
  entry_file: string;
  selected_selector?: string | null;
  selected_html_snippet?: string | null;
  selected_meta?: Record<string, unknown>;
};

export default function DesignPreviewPage() {
  const searchParams = useSearchParams();
  const [path, setPath] = React.useState(searchParams.get("path") || "");
  const [entry, setEntry] = React.useState(searchParams.get("entry") || "index.html");
  const [session, setSession] = React.useState<PreviewSession | null>(null);
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const [skillMessage, setSkillMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const openPreview = React.useCallback(async () => {
    if (!path.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    setSkillMessage(null);
    try {
      const response = await ceApi("/api/design/preview/open", {
        method: "POST",
        body: JSON.stringify({ path: path.trim(), entry: entry.trim() || "index.html" }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(parseApiErrorMessage(payload, "Could not open preview"));
      }
      setSession((payload as { session: PreviewSession }).session);
      setPreviewUrl((payload as { preview_url: string }).preview_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open preview");
    } finally {
      setBusy(false);
    }
  }, [entry, path]);

  React.useEffect(() => {
    if (searchParams.get("path")) {
      void openPreview();
    }
  }, [openPreview, searchParams]);

  const onSelection = React.useCallback((payload: Record<string, unknown>) => {
    setSkillMessage(null);
    setSession((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        selected_selector: String(payload.selector || ""),
        selected_html_snippet: String(payload.html_snippet || ""),
        selected_meta: (payload.meta as Record<string, unknown>) || {},
      };
    });
  }, []);

  const loadSkillMessage = async () => {
    if (!session) {
      return;
    }
    const response = await ceApi(`/api/design/preview/${encodeURIComponent(session.session_id)}/skill-message`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(parseApiErrorMessage(payload, "Could not build skill message"));
    }
    setSkillMessage((payload as { message: string }).message);
  };

  return (
    <Box>
      <Typography variant="h5" component="h1" sx={{ mb: 2 }}>
        Design live preview
      </Typography>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "flex-end" }}>
            <TextField
              label="HTML file or project path"
              value={path}
              onChange={(event) => setPath(event.target.value)}
              fullWidth
              size="small"
            />
            <TextField label="Entry" value={entry} onChange={(event) => setEntry(event.target.value)} size="small" />
            <Button variant="contained" disabled={!path.trim() || busy} onClick={() => void openPreview()}>
              {busy ? "Opening..." : "Open preview"}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 360px" }, gap: 2 }}>
        <PreviewFrame sessionId={session?.session_id || null} previewUrl={previewUrl} onSelection={onSelection} />
        <Card variant="outlined">
          <CardContent>
            <ComponentInspector
              selector={session?.selected_selector}
              snippet={session?.selected_html_snippet}
              meta={session?.selected_meta}
              skillMessage={skillMessage}
              onLoadSkillMessage={loadSkillMessage}
            />
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}

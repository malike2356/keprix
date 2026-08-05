"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useParams } from "next/navigation";
import PageHeader from "@/components/ui/PageHeader";
import MarkdownRenderer from "@/components/workspace/MarkdownRenderer";
import { fetchSharedDocument, type WorkspaceDocument } from "@/lib/workspace-api";

export default function SharedDocumentPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token || "";
  const [doc, setDoc] = React.useState<WorkspaceDocument | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!token) return;
    void (async () => {
      setLoading(true);
      try {
        setDoc(await fetchSharedDocument(token));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Shared document not found");
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  return (
    <Box sx={{ maxWidth: 880, mx: "auto", p: 3 }}>
      <PageHeader title="Shared document" description="Read-only shared workspace document." />
      {loading ? <CircularProgress size={24} /> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}
      {doc ? (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h4" sx={{ mb: 2 }}>
            {doc.title}
          </Typography>
          <MarkdownRenderer content={doc.content || "_Empty_"} />
        </Box>
      ) : null}
    </Box>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { extractIntent, fetchIntentSchemas } from "@/lib/platform-admin-api";

export default function IntentAdminPage() {
  const [text, setText] = React.useState("Book a meeting tomorrow at 3pm");
  const [result, setResult] = React.useState<unknown>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const schemas = useSWR("intent-schemas", () => fetchIntentSchemas());
  const items = Array.isArray(schemas.data) ? schemas.data : [];

  return (
    <Box>
      <PageHeader title="Intent schemas" description="Browse intent schemas and run extract smoke tests." breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Intent" }]} />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {items.length === 0 && !schemas.isLoading ? (
        <EmptyState title="No schemas" description="Register schemas via POST /api/intent/register (admin)." />
      ) : (
        <Box sx={{ mb: 2 }}><StructuredDataView value={items} /></Box>
      )}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={1.5}>
          <TextField multiline minRows={3} label="Text" value={text} onChange={(e) => setText(e.target.value)} />
          <Button variant="contained" disabled={busy} onClick={async () => {
            setBusy(true); setError(null);
            try { setResult(await extractIntent({ translated_text: text })); }
            catch (err) { setError(err instanceof Error ? err.message : "Extract failed"); }
            finally { setBusy(false); }
          }}>Extract intent</Button>
        </Stack>
        {result ? <Box sx={{ mt: 1 }}><StructuredDataView value={result} /></Box> : null}
      </Paper>
    </Box>
  );
}

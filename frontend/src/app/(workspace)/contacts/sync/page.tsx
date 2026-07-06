"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchGoogleAuthUrl,
  fetchMicrosoftAuthUrl,
  fetchSyncSources,
  importContactsFile,
  triggerSync,
  type SyncSource,
} from "@/lib/contacts-api";

export default function ContactsSyncPage() {
  const [sources, setSources] = React.useState<SyncSource[]>([]);
  const [carddavUrl, setCarddavUrl] = React.useState("");
  const [carddavUser, setCarddavUser] = React.useState("");
  const [carddavPassword, setCarddavPassword] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setSources(await fetchSyncSources());
  }, []);

  React.useEffect(() => {
    reload().catch(() => setSources([]));
  }, [reload]);

  const connectGoogle = async () => {
    try {
      window.location.href = await fetchGoogleAuthUrl();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google auth failed");
    }
  };

  const connectMicrosoft = async () => {
    try {
      window.location.href = await fetchMicrosoftAuthUrl();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microsoft auth failed");
    }
  };

  const addCarddav = async () => {
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_CE_API_URL || ""}/api/contacts/sync/sources`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            display_name: "CardDAV",
            carddav_url: carddavUrl,
            carddav_username: carddavUser,
            carddav_password: carddavPassword,
          }),
        },
      );
      if (!response.ok) {
        throw new Error("CardDAV setup failed");
      }
      setMessage("CardDAV source added");
      setCarddavPassword("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CardDAV setup failed");
    }
  };

  const onImport = async (kind: "vcf" | "csv", file?: File | null) => {
    if (!file) {
      return;
    }
    try {
      const summary = await importContactsFile(file, kind);
      setMessage(`Import complete: ${summary.added} added, ${summary.updated} updated`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Contact sync"
        description="Connect Google, Outlook, CardDAV, or import files."
        breadcrumbs={[
          { label: "Contacts", href: "/contacts" },
          { label: "Sync" },
        ]}
      />
      {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
        <Button variant="contained" onClick={connectGoogle}>Connect Google Contacts</Button>
        <Button variant="outlined" onClick={connectMicrosoft}>Connect Outlook</Button>
      </Box>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>CardDAV account</Typography>
          <Box sx={{ display: "grid", gap: 1.5, maxWidth: 520 }}>
            <TextField label="Server URL" value={carddavUrl} onChange={(e) => setCarddavUrl(e.target.value)} />
            <TextField label="Username" value={carddavUser} onChange={(e) => setCarddavUser(e.target.value)} />
            <TextField label="Password" type="password" value={carddavPassword} onChange={(e) => setCarddavPassword(e.target.value)} />
            <Button variant="outlined" onClick={addCarddav}>Add CardDAV source</Button>
          </Box>
        </CardContent>
      </Card>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Import</Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button component="label" variant="outlined">
              Import vCard
              <input hidden type="file" accept=".vcf,.vcard" onChange={(e) => onImport("vcf", e.target.files?.[0])} />
            </Button>
            <Button component="label" variant="outlined">
              Import CSV
              <input hidden type="file" accept=".csv" onChange={(e) => onImport("csv", e.target.files?.[0])} />
            </Button>
          </Box>
        </CardContent>
      </Card>
      <Typography variant="h6" gutterBottom>Connected sources</Typography>
      {sources.length === 0 ? (
        <Typography color="text.secondary">No sync sources configured.</Typography>
      ) : (
        sources.map((source) => (
          <Card key={source.id} sx={{ mb: 1 }}>
            <CardContent sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Box>
                <Typography fontWeight={600}>{source.display_name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {source.provider} | {source.contact_count || 0} contacts
                </Typography>
                {source.last_sync_error && (
                  <Typography variant="body2" color="error">{source.last_sync_error}</Typography>
                )}
              </Box>
              <Button onClick={() => triggerSync(source.id).then(reload)}>Sync now</Button>
            </CardContent>
          </Card>
        ))
      )}
    </Box>
  );
}

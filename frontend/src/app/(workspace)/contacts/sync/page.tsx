"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import LinkIcon from "@mui/icons-material/Link";
import SyncIcon from "@mui/icons-material/Sync";
import * as React from "react";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import {
  createCardDavSource,
  deleteSyncSource,
  fetchGoogleAuthUrl,
  fetchGoogleOAuthConfig,
  fetchMicrosoftAuthUrl,
  fetchSyncSources,
  importContactsFile,
  saveGoogleOAuthConfig,
  triggerSync,
  type GoogleOAuthConfig,
  type SyncSource,
} from "@/lib/contacts-api";

type CardDavPreset = {
  id: string;
  label: string;
  url_hint: string;
  help: string;
};

const CARDDAV_PRESETS: CardDavPreset[] = [
  {
    id: "icloud",
    label: "Apple iCloud",
    url_hint: "https://contacts.icloud.com/",
    help: "Use your Apple ID email and an app-specific password.",
  },
  {
    id: "nextcloud",
    label: "Nextcloud",
    url_hint: "https://cloud.example/remote.php/dav/addressbooks/users/YOU/contacts/",
    help: "CardDAV address book URL plus Nextcloud login / app password.",
  },
  {
    id: "fastmail",
    label: "Fastmail",
    url_hint: "https://carddav.fastmail.com/dav/addressbooks/user/you@fastmail.com/Default",
    help: "Fastmail CardDAV URL with an app password.",
  },
  {
    id: "generic",
    label: "Generic CardDAV",
    url_hint: "https://carddav.example.com/",
    help: "Any CardDAV server (Radicale, Synology, Baikal, etc.).",
  },
];

const INTERVAL_OPTIONS = [
  { label: "15 min", value: 15 },
  { label: "30 min", value: 30 },
  { label: "1 hour", value: 60 },
  { label: "6 hours", value: 360 },
  { label: "24 hours", value: 1440 },
];

export default function ContactsSyncPage() {
  const [sources, setSources] = React.useState<SyncSource[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [showCarddav, setShowCarddav] = React.useState(false);
  const [presetId, setPresetId] = React.useState("icloud");
  const [displayName, setDisplayName] = React.useState("Apple iCloud");
  const [carddavUrl, setCarddavUrl] = React.useState("");
  const [carddavUser, setCarddavUser] = React.useState("");
  const [carddavPassword, setCarddavPassword] = React.useState("");
  const [intervalMinutes, setIntervalMinutes] = React.useState(60);
  const [saving, setSaving] = React.useState(false);
  const [syncingId, setSyncingId] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [googleConfig, setGoogleConfig] = React.useState<GoogleOAuthConfig | null>(null);
  const [googleModalOpen, setGoogleModalOpen] = React.useState(false);
  const [googleClientId, setGoogleClientId] = React.useState("");
  const [googleClientSecret, setGoogleClientSecret] = React.useState("");
  const [googleSaving, setGoogleSaving] = React.useState(false);

  const preset = CARDDAV_PRESETS.find((item) => item.id === presetId) || CARDDAV_PRESETS[0];

  const reload = React.useCallback(async () => {
    setLoading(true);
    try {
      const [nextSources, nextGoogle] = await Promise.all([
        fetchSyncSources(),
        fetchGoogleOAuthConfig().catch(() => null),
      ]);
      setSources(nextSources);
      if (nextGoogle) setGoogleConfig(nextGoogle);
      setError(null);
    } catch (err) {
      setSources([]);
      setError(err instanceof Error ? err.message : "Failed to load sync sources");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const oauthError = params.get("error");
    if (!connected && !oauthError) return;
    if (oauthError) {
      setError(`OAuth (${connected || "provider"}): ${oauthError}`);
    } else if (connected) {
      setMessage(`Connected ${connected}. Contacts sync started.`);
    }
    params.delete("connected");
    params.delete("error");
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
    window.history.replaceState({}, "", next);
    void reload();
  }, [reload]);

  function applyPreset(nextId: string) {
    setPresetId(nextId);
    const next = CARDDAV_PRESETS.find((item) => item.id === nextId);
    if (!next) return;
    setDisplayName(next.label);
  }

  async function connectGoogle() {
    setError(null);
    try {
      const config = googleConfig || (await fetchGoogleOAuthConfig());
      setGoogleConfig(config);
      if (!config.configured) {
        setGoogleModalOpen(true);
        return;
      }
      window.location.href = await fetchGoogleAuthUrl();
    } catch (err) {
      setGoogleModalOpen(true);
      setError(err instanceof Error ? err.message : "Google auth is not configured");
    }
  }

  async function saveGoogleCredentialsAndConnect() {
    if (!googleClientId.trim() || !googleClientSecret.trim()) {
      setError("Client ID and Client Secret are required");
      return;
    }
    setGoogleSaving(true);
    setError(null);
    try {
      const saved = await saveGoogleOAuthConfig({
        client_id: googleClientId.trim(),
        client_secret: googleClientSecret.trim(),
      });
      setGoogleConfig(saved);
      setGoogleClientSecret("");
      setGoogleModalOpen(false);
      setMessage("Google OAuth app saved. Continuing to Google consent…");
      window.location.href = await fetchGoogleAuthUrl();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save Google credentials");
    } finally {
      setGoogleSaving(false);
    }
  }

  async function connectMicrosoft() {
    setError(null);
    try {
      window.location.href = await fetchMicrosoftAuthUrl();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microsoft auth is not configured");
    }
  }

  async function addCarddav() {
    if (!carddavUrl.trim() || !carddavUser.trim() || !carddavPassword) {
      setError("Server URL, username, and password are required");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const created = await createCardDavSource({
        display_name: displayName.trim() || preset.label,
        carddav_url: carddavUrl.trim(),
        carddav_username: carddavUser.trim(),
        carddav_password: carddavPassword,
        sync_interval_minutes: intervalMinutes,
      });
      const initial = created.initial_sync || {};
      if (initial.error) {
        setError(`CardDAV saved, but sync failed: ${String(initial.error)}`);
      } else {
        setMessage(
          `CardDAV connected. Synced ${Number(initial.added || 0)} added, ${Number(initial.updated || 0)} updated.`,
        );
      }
      setCarddavPassword("");
      setCarddavUrl("");
      setCarddavUser("");
      setShowCarddav(false);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CardDAV setup failed");
    } finally {
      setSaving(false);
    }
  }

  async function onImport(kind: "vcf" | "csv", file?: File | null) {
    if (!file) return;
    setError(null);
    setMessage(null);
    try {
      const summary = await importContactsFile(file, kind);
      setMessage(`Import complete: ${summary.added ?? 0} added, ${summary.updated ?? 0} updated`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    }
  }

  async function handleSync(sourceId: string) {
    setSyncingId(sourceId);
    setError(null);
    try {
      const result = await triggerSync(sourceId);
      if (result.error) {
        setError(String(result.error));
      } else {
        setMessage(
          `Synced: ${Number(result.added || 0)} added, ${Number(result.updated || 0)} updated`,
        );
      }
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncingId(null);
    }
  }

  async function handleRemove(source: SyncSource) {
    if (!window.confirm(`Remove "${source.display_name}"?`)) return;
    try {
      await deleteSyncSource(source.id);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove source");
    }
  }

  return (
    <Box>
      <PageHeader
        title="Contact sync"
        description="Connect Google, Outlook, or CardDAV, then sync on an interval. Import vCard/CSV when you need a one-off load."
        breadcrumbs={[
          { label: "Contacts", href: "/contacts" },
          { label: "Sync" },
        ]}
      />

      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Box
        sx={{
          mb: 3,
          p: 2,
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          display: "grid",
          gap: 1.5,
        }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Connect a source
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Prefer Google or Outlook OAuth when configured. Otherwise use CardDAV (iCloud, Nextcloud, Fastmail) with an
          app password.
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button variant="contained" startIcon={<LinkIcon />} onClick={() => void connectGoogle()}>
            Connect Google Contacts
          </Button>
          <Button variant="outlined" onClick={() => setGoogleModalOpen(true)}>
            {googleConfig?.configured ? "Edit Google OAuth app" : "Set Google OAuth credentials"}
          </Button>
          <Button variant="outlined" onClick={() => void connectMicrosoft()}>
            Connect Outlook
          </Button>
          <Button variant="outlined" onClick={() => setShowCarddav((value) => !value)}>
            {showCarddav ? "Hide CardDAV" : "Add CardDAV"}
          </Button>
        </Stack>
        {googleConfig?.configured ? (
          <Typography variant="body2" color="text.secondary">
            Google OAuth ready ({googleConfig.source}): {googleConfig.client_id_masked}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Google needs your Cloud Console Client ID and Secret. Use Set Google OAuth credentials first.
          </Typography>
        )}

        <Collapse in={showCarddav}>
          <Box sx={{ display: "grid", gap: 1.5, pt: 1, maxWidth: 560 }}>
            <FormControl fullWidth>
              <InputLabel id="carddav-preset-label">Provider</InputLabel>
              <Select
                labelId="carddav-preset-label"
                label="Provider"
                value={presetId}
                onChange={(e) => applyPreset(String(e.target.value))}
              >
                {CARDDAV_PRESETS.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="body2" color="text.secondary">
              {preset.help}
            </Typography>
            <TextField
              label="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="off"
            />
            <TextField
              label="Server URL"
              value={carddavUrl}
              onChange={(e) => setCarddavUrl(e.target.value)}
              placeholder={preset.url_hint}
              autoComplete="off"
            />
            <TextField
              label="Username"
              value={carddavUser}
              onChange={(e) => setCarddavUser(e.target.value)}
              autoComplete="off"
            />
            <TextField
              label="Password / app password"
              type="password"
              value={carddavPassword}
              onChange={(e) => setCarddavPassword(e.target.value)}
              autoComplete="new-password"
            />
            <FormControl fullWidth>
              <InputLabel id="contacts-interval-label">Resync interval</InputLabel>
              <Select
                labelId="contacts-interval-label"
                label="Resync interval"
                value={intervalMinutes}
                onChange={(e) => setIntervalMinutes(Number(e.target.value))}
              >
                {INTERVAL_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    Every {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={() => void addCarddav()} disabled={saving}>
              Add CardDAV source
            </Button>
          </Box>
        </Collapse>
      </Box>

      <Box
        sx={{
          mb: 3,
          p: 2,
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          display: "grid",
          gap: 1.5,
        }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Import file
        </Typography>
        <Typography variant="body2" color="text.secondary">
          One-off import. Does not create a recurring sync source.
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button component="label" variant="outlined">
            Import vCard
            <input hidden type="file" accept=".vcf,.vcard" onChange={(e) => void onImport("vcf", e.target.files?.[0])} />
          </Button>
          <Button component="label" variant="outlined">
            Import CSV
            <input hidden type="file" accept=".csv" onChange={(e) => void onImport("csv", e.target.files?.[0])} />
          </Button>
        </Stack>
      </Box>

      <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
        Connected sources
      </Typography>
      {loading ? (
        <Typography variant="body2" color="text.secondary">
          Loading sources…
        </Typography>
      ) : sources.length === 0 ? (
        <EmptyState
          title="No sync sources"
          description="Connect Google, Outlook, or CardDAV to keep contacts updated automatically."
          icon={<SyncIcon sx={{ fontSize: 40 }} />}
          actionLabel="Add CardDAV"
          onAction={() => setShowCarddav(true)}
        />
      ) : (
        <Stack spacing={1}>
          {sources.map((source) => (
            <Box
              key={source.id}
              sx={{
                display: "flex",
                justifyContent: "space-between",
                gap: 1,
                flexWrap: "wrap",
                p: 1.5,
                border: 1,
                borderColor: "divider",
                borderRadius: 1,
              }}
            >
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography sx={{ fontWeight: 600 }}>{source.display_name}</Typography>
                  <Chip size="small" label={source.provider} />
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`every ${source.sync_interval_minutes || 60}m`}
                  />
                  <Chip size="small" label={`${source.contact_count || 0} contacts`} />
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                  {source.last_delta_sync_at || source.last_full_sync_at
                    ? `Last sync: ${new Date(String(source.last_delta_sync_at || source.last_full_sync_at)).toLocaleString()}`
                    : "Not synced yet"}
                </Typography>
                {source.last_sync_error ? (
                  <Typography variant="body2" color="error" sx={{ mt: 0.5 }}>
                    {source.last_sync_error}
                  </Typography>
                ) : null}
              </Box>
              <Stack direction="row" spacing={1}>
                <Button
                  size="small"
                  startIcon={<SyncIcon fontSize="small" />}
                  onClick={() => void handleSync(source.id)}
                  disabled={syncingId === source.id}
                >
                  Sync now
                </Button>
                <Button size="small" color="error" onClick={() => void handleRemove(source)}>
                  Remove
                </Button>
              </Stack>
            </Box>
          ))}
        </Stack>
      )}

      <Dialog open={googleModalOpen} onClose={() => setGoogleModalOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Google Contacts OAuth credentials</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Create an OAuth client (Web application) in Google Cloud Console, enable People API, then paste the
            Client ID and Client Secret here. Add this exact Authorized redirect URI:
          </Typography>
          <TextField
            label="Authorized redirect URI (copy into Google Cloud)"
            value={googleConfig?.redirect_uri || "http://localhost:3334/api/contacts/sync/google/callback"}
            InputProps={{ readOnly: true }}
            onFocus={(e) => e.target.select()}
          />
          {googleConfig?.configured ? (
            <Alert severity="info">
              Saved client: {googleConfig.client_id_masked}. Enter a new secret to replace credentials.
            </Alert>
          ) : null}
          <TextField
            label="Client ID"
            value={googleClientId}
            onChange={(e) => setGoogleClientId(e.target.value)}
            placeholder="123456789-abc.apps.googleusercontent.com"
            autoComplete="off"
          />
          <TextField
            label="Client Secret"
            type="password"
            value={googleClientSecret}
            onChange={(e) => setGoogleClientSecret(e.target.value)}
            autoComplete="new-password"
          />
          <Typography variant="caption" color="text.secondary">
            {googleConfig?.people_api_hint || "Enable People API on the same Google Cloud project."}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGoogleModalOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={googleSaving}
            onClick={() => void saveGoogleCredentialsAndConnect()}
          >
            {googleSaving ? "Saving…" : "Save and connect Google"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

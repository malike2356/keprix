"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SearchIcon from "@mui/icons-material/Search";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import {
  activateWebSearchProvider,
  deleteWebSearchSettings,
  fetchWebSearchSettings,
  saveWebSearchSettings,
  testWebSearchProvider,
  type WebSearchCatalogItem,
} from "@/lib/admin-workspace-api";

export default function WebSearchSettingsPage() {
  const { data, mutate, error, isLoading } = useSWR("web-search-settings", fetchWebSearchSettings);
  const [dialogProvider, setDialogProvider] = React.useState<WebSearchCatalogItem | null>(null);
  const [envValues, setEnvValues] = React.useState<Record<string, string>>({});
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [messageSeverity, setMessageSeverity] = React.useState<"success" | "error" | "info">("info");

  const openDialog = (provider: WebSearchCatalogItem) => {
    setDialogProvider(provider);
    setEnvValues({});
    setMessage(null);
  };

  const showMessage = (text: string, severity: "success" | "error" | "info" = "info") => {
    setMessage(text);
    setMessageSeverity(severity);
  };

  const catalog = data?.catalog || [];
  const providers = data?.providers || {};

  return (
    <Box>
      <PageHeader
        title="Web search"
        description="Choose and configure the search provider used by deep research and web tools."
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Could not load web search settings"}
        </Alert>
      ) : null}

      {message ? (
        <Alert severity={messageSeverity} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Alert severity="info" sx={{ mb: 2 }}>
        Credentials are saved through the server. You do not need to edit `.env` manually. After saving, retry deep
        research at <Link href="/research">/research</Link>.
      </Alert>

      <Stack spacing={1.5}>
        {isLoading ? (
          <SkeletonList rows={4} rowHeight={88} />
        ) : (
          <>
            {catalog.map((provider) => {
          const state = providers[provider.id];
          const connected = Boolean(state?.connected);
          const active = Boolean(state?.is_active);
          return (
            <Card key={provider.id} variant="outlined">
              <CardContent sx={{ display: "grid", gap: 1.5 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
                  <Box sx={{ minWidth: 0 }}>
                    <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                      <SearchIcon fontSize="small" color="action" />
                      <Typography variant="subtitle1">{provider.label}</Typography>
                      {provider.badge ? <Chip size="small" label={provider.badge} /> : null}
                      {active ? <Chip size="small" color="primary" label="Active for research" /> : null}
                      {connected ? (
                        <Chip size="small" color="success" icon={<CheckCircleIcon />} label="Configured" />
                      ) : (
                        <Chip size="small" label="Not configured" />
                      )}
                    </Stack>
                    {provider.description ? (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        {provider.description}
                      </Typography>
                    ) : null}
                  </Box>
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                    <Button size="small" variant="outlined" onClick={() => openDialog(provider)}>
                      {connected ? "Update" : "Configure"}
                    </Button>
                    {connected ? (
                      <Button
                        size="small"
                        variant="text"
                        disabled={busy || active}
                        onClick={() => {
                          setBusy(true);
                          void activateWebSearchProvider(provider.id)
                            .then(() => mutate())
                            .then(() => showMessage(`${provider.label} is now active for research.`, "success"))
                            .catch((err: unknown) =>
                              showMessage(err instanceof Error ? err.message : "Could not activate provider", "error"),
                            )
                            .finally(() => setBusy(false));
                        }}
                      >
                        Use for research
                      </Button>
                    ) : null}
                    {connected ? (
                      <Button
                        size="small"
                        color="error"
                        disabled={busy}
                        onClick={() => {
                          if (!window.confirm(`Remove credentials for ${provider.label}?`)) return;
                          setBusy(true);
                          void deleteWebSearchSettings(provider.id)
                            .then(() => mutate())
                            .then(() => showMessage(`Removed ${provider.label} credentials.`, "success"))
                            .catch((err: unknown) =>
                              showMessage(err instanceof Error ? err.message : "Could not remove provider", "error"),
                            )
                            .finally(() => setBusy(false));
                        }}
                      >
                        Remove
                      </Button>
                    ) : null}
                  </Stack>
                </Box>
              </CardContent>
            </Card>
          );
        })}
            {!catalog.length && !error ? (
              <Typography variant="body2" color="text.secondary">
                No web search providers are available.
              </Typography>
            ) : null}
          </>
        )}
      </Stack>

      <Dialog open={Boolean(dialogProvider)} onClose={() => setDialogProvider(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{dialogProvider ? `Configure ${dialogProvider.label}` : "Configure provider"}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <DialogContentText>
            Leave secret fields blank to keep existing values. Saving also activates this provider for deep research.
          </DialogContentText>
          {(dialogProvider?.env_vars || []).map((field) => (
            <Box key={field.key}>
              <TextField
                label={field.prompt || field.key}
                type={field.secret === false ? "text" : "password"}
                value={envValues[field.key] || ""}
                onChange={(e) => setEnvValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                fullWidth
                helperText={
                  field.url ? (
                    <>
                      Get credentials at{" "}
                      <Link href={field.url} target="_blank" rel="noopener noreferrer">
                        {field.url}
                        <OpenInNewIcon sx={{ fontSize: 14, ml: 0.5, verticalAlign: "text-bottom" }} />
                      </Link>
                    </>
                  ) : (
                    "Optional for providers that do not require credentials."
                  )
                }
              />
            </Box>
          ))}
          {!dialogProvider?.env_vars?.length ? (
            <Typography variant="body2" color="text.secondary">
              This provider does not require credentials. Save to activate it for research.
            </Typography>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              if (!dialogProvider) return;
              void testWebSearchProvider(dialogProvider.id).then((result) =>
                showMessage(result.message, result.ok ? "success" : "error"),
              );
            }}
            disabled={!dialogProvider}
          >
            Test connection
          </Button>
          <Button
            variant="contained"
            disabled={busy || !dialogProvider}
            onClick={() => {
              if (!dialogProvider) return;
              setBusy(true);
              void saveWebSearchSettings(dialogProvider.id, {
                env_values: envValues,
                set_active: true,
              })
                .then(() => {
                  setDialogProvider(null);
                  return mutate();
                })
                .then(() => showMessage(`${dialogProvider.label} saved and activated for research.`, "success"))
                .catch((err: unknown) =>
                  showMessage(err instanceof Error ? err.message : "Could not save provider", "error"),
                )
                .finally(() => setBusy(false));
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

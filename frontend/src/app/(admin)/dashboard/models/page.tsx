"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import LlmProvidersPanel from "@/components/admin/LlmProvidersPanel";
import ModelsAdminTable from "@/components/admin/ModelsAdminTable";
import PageContainer from "@/components/shared/PageContainer";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import {
  createCustomProvider,
  deleteCustomProvider,
  deleteProviderSettings,
  fetchAdminSettings,
  saveProviderSettings,
  setDefaultProvider,
  testProviderConnection,
  updateCustomProvider,
  type CustomProvider,
} from "@/lib/admin-workspace-api";
import { useRequireAdmin } from "@/lib/ce-auth";

const FALLBACK_PROVIDERS = [
  { id: "deepseek", label: "DeepSeek" },
  { id: "anthropic", label: "Anthropic" },
  { id: "openai", label: "OpenAI" },
  { id: "google", label: "Gemini" },
  { id: "ollama", label: "Ollama" },
];

export default function AdminModelsPage() {
  useRequireAdmin();
  const { data, mutate } = useSWR("admin-settings", fetchAdminSettings);
  const [providerDialog, setProviderDialog] = React.useState<string | null>(null);
  const [customDialogOpen, setCustomDialogOpen] = React.useState(false);
  const [editingCustomId, setEditingCustomId] = React.useState<string | null>(null);
  const [providerKey, setProviderKey] = React.useState("");
  const [providerModel, setProviderModel] = React.useState("");
  const [customName, setCustomName] = React.useState("");
  const [customBaseUrl, setCustomBaseUrl] = React.useState("http://localhost:11434/v1");
  const [customApiKey, setCustomApiKey] = React.useState("");
  const [customModel, setCustomModel] = React.useState("");
  const [testMessage, setTestMessage] = React.useState<string | null>(null);
  const [providerBusy, setProviderBusy] = React.useState(false);

  if (!data) {
    return (
      <PageContainer title="Models" description="Configured LLM providers and model IDs." padded={false}>
        <SkeletonDetailPanel fields={5} />
      </PageContainer>
    );
  }

  const providerRows = data.provider_catalog?.length ? data.provider_catalog : FALLBACK_PROVIDERS;
  const customProviders = data.custom_providers || [];

  const openBuiltinDialog = (providerId: string) => {
    const state = data.providers?.[providerId];
    setProviderDialog(providerId);
    setProviderKey("");
    setProviderModel(state?.default_model || "");
    setTestMessage(null);
  };

  const openCustomDialog = (provider?: CustomProvider) => {
    setEditingCustomId(provider?.id || null);
    setCustomName(provider?.name || "");
    setCustomBaseUrl(provider?.base_url || "http://localhost:11434/v1");
    setCustomApiKey("");
    setCustomModel(provider?.default_model || "");
    setCustomDialogOpen(true);
    setTestMessage(null);
  };

  return (
    <PageContainer
      title="Models"
      description="Manage LLM providers, default models, and connection credentials."
      padded={false}
    >
      <Box sx={{ display: "grid", gap: 2 }}>
        <ModelsAdminTable />

        <Typography variant="subtitle2" sx={{ fontWeight: 600, pt: 1 }}>
          Provider credentials
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Enable providers here; advanced instance settings remain under Settings.
        </Typography>

        <LlmProvidersPanel
          providerRows={providerRows}
          providers={data.providers}
          customProviders={customProviders}
          busy={providerBusy}
          onConfigureBuiltin={openBuiltinDialog}
          onRemoveBuiltin={async (providerId) => {
            if (!window.confirm(`Remove credentials for ${providerId}?`)) return;
            setProviderBusy(true);
            try {
              await deleteProviderSettings(providerId);
              await mutate();
              setTestMessage(`Removed ${providerId} credentials`);
            } finally {
              setProviderBusy(false);
            }
          }}
          onMakeDefault={async (providerId) => {
            setProviderBusy(true);
            try {
              await setDefaultProvider(providerId);
              await mutate();
              setTestMessage(`Set ${providerId} as default provider`);
            } finally {
              setProviderBusy(false);
            }
          }}
          onConfigureCustom={openCustomDialog}
          onRemoveCustom={async (providerId) => {
            if (!window.confirm("Delete this custom provider?")) return;
            setProviderBusy(true);
            try {
              await deleteCustomProvider(providerId);
              await mutate();
            } finally {
              setProviderBusy(false);
            }
          }}
        />

        {testMessage ? (
          <Typography variant="body2" color="text.secondary">
            {testMessage}
          </Typography>
        ) : null}
      </Box>

      <Dialog open={Boolean(providerDialog)} onClose={() => setProviderDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure {providerDialog}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField
            label="API key"
            type="password"
            value={providerKey}
            onChange={(event) => setProviderKey(event.target.value)}
            fullWidth
          />
          <TextField
            label="Default model ID"
            value={providerModel}
            onChange={(event) => setProviderModel(event.target.value)}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProviderDialog(null)}>Cancel</Button>
          <Button
            onClick={() => {
              if (!providerDialog) return;
              void testProviderConnection(providerDialog).then((result) => setTestMessage(result.message));
            }}
          >
            Test connection
          </Button>
          <Button
            variant="contained"
            disabled={providerBusy}
            onClick={() => {
              if (!providerDialog) return;
              setProviderBusy(true);
              void saveProviderSettings(providerDialog, {
                api_key: providerKey || undefined,
                default_model: providerModel || undefined,
              })
                .then(() => {
                  setProviderDialog(null);
                  return mutate();
                })
                .finally(() => setProviderBusy(false));
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={customDialogOpen} onClose={() => setCustomDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingCustomId ? "Edit custom provider" : "Add custom provider"}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField label="Name" value={customName} onChange={(e) => setCustomName(e.target.value)} fullWidth />
          <TextField label="Base URL" value={customBaseUrl} onChange={(e) => setCustomBaseUrl(e.target.value)} fullWidth />
          <TextField label="API key" type="password" value={customApiKey} onChange={(e) => setCustomApiKey(e.target.value)} fullWidth />
          <TextField label="Default model" value={customModel} onChange={(e) => setCustomModel(e.target.value)} fullWidth />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCustomDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={async () => {
              setProviderBusy(true);
              try {
                if (editingCustomId) {
                  await updateCustomProvider(editingCustomId, {
                    name: customName,
                    base_url: customBaseUrl,
                    api_key: customApiKey || undefined,
                    default_model: customModel,
                  });
                } else {
                  await createCustomProvider({
                    name: customName,
                    base_url: customBaseUrl,
                    api_key: customApiKey,
                    default_model: customModel,
                  });
                }
                await mutate();
                setCustomDialogOpen(false);
              } finally {
                setProviderBusy(false);
              }
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </PageContainer>
  );
}

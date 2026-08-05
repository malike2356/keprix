"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import LlmProvidersPanel from "@/components/admin/LlmProvidersPanel";
import SettingsOperatorSections from "@/components/admin/SettingsOperatorSections";
import BlankCard from "@/components/cards/BlankCard";
import PageContainer from "@/components/shared/PageContainer";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import {
  createCustomProvider,
  deleteCustomProvider,
  deleteProviderSettings,
  fetchAdminSettings,
  saveAdminSettings,
  saveProviderSettings,
  setDefaultProvider,
  testCustomProviderConnection,
  testProviderConnection,
  updateCustomProvider,
  type AdminSettings,
  type CustomProvider,
} from "@/lib/admin-workspace-api";

const FALLBACK_PROVIDERS = [
  { id: "deepseek", label: "DeepSeek" },
  { id: "anthropic", label: "Anthropic" },
  { id: "openai", label: "OpenAI" },
  { id: "google", label: "Gemini" },
  { id: "ollama", label: "Ollama" },
];

export default function AdminSettingsPage() {
  const { data, mutate } = useSWR("admin-settings", fetchAdminSettings);
  const [tab, setTab] = React.useState(0);
  const [settings, setSettings] = React.useState<AdminSettings | null>(null);
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

  React.useEffect(() => {
    if (data?.settings) setSettings(data.settings);
  }, [data]);

  if (!settings) {
    return (
      <PageContainer title="Settings" description="Instance configuration." padded={false}>
        <SkeletonDetailPanel fields={5} />
      </PageContainer>
    );
  }

  const save = async () => {
    await saveAdminSettings(settings);
    await mutate();
  };

  const providerRows = data?.provider_catalog?.length ? data.provider_catalog : FALLBACK_PROVIDERS;
  const customProviders = data?.custom_providers || [];
  const tabs = ["General", "LLM Providers", "Agent behaviour", "Storage"];
  if (data?.governance_enabled) tabs.push("Governance connector");

  const openBuiltinDialog = (providerId: string) => {
    const state = data?.providers?.[providerId];
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

  const makeDefault = async (providerId: string) => {
    setProviderBusy(true);
    try {
      await setDefaultProvider(providerId);
      await mutate();
      setTestMessage(`Set ${providerId} as default provider`);
    } catch (err) {
      setTestMessage(err instanceof Error ? err.message : "Could not set default provider");
    } finally {
      setProviderBusy(false);
    }
  };

  const removeBuiltinProvider = async (providerId: string) => {
    if (!window.confirm(`Remove credentials for ${providerId}?`)) return;
    setProviderBusy(true);
    try {
      await deleteProviderSettings(providerId);
      await mutate();
      setTestMessage(`Removed ${providerId} credentials`);
    } catch (err) {
      setTestMessage(err instanceof Error ? err.message : "Could not remove provider");
    } finally {
      setProviderBusy(false);
    }
  };

  const removeCustomProvider = async (providerId: string) => {
    if (!window.confirm("Delete this custom provider?")) return;
    setProviderBusy(true);
    try {
      await deleteCustomProvider(providerId);
      await mutate();
      setTestMessage("Custom provider deleted");
    } catch (err) {
      setTestMessage(err instanceof Error ? err.message : "Could not delete custom provider");
    } finally {
      setProviderBusy(false);
    }
  };

  return (
    <PageContainer title="Settings" description="Configure your Keprix instance." padded={false}>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "220px 1fr" }, gap: 2 }}>
        <BlankCard>
          <Tabs
            orientation="vertical"
            value={tab}
            onChange={(_, value) => setTab(value)}
            sx={{ borderRight: 1, borderColor: "divider", minHeight: 320 }}
          >
            {tabs.map((label) => (
              <Tab key={label} label={label} sx={{ alignItems: "flex-start" }} />
            ))}
          </Tabs>
        </BlankCard>

        <BlankCard>
          <Box sx={{ p: 3, display: "grid", gap: 2 }}>
            {tab === 0 ? (
              <>
                <TextField label="Instance name" value={settings.instance_name} onChange={(e) => setSettings({ ...settings, instance_name: e.target.value })} />
                <TextField label="Instance URL" value={settings.instance_url} onChange={(e) => setSettings({ ...settings, instance_url: e.target.value })} />
                <TextField label="Timezone" value={settings.timezone} onChange={(e) => setSettings({ ...settings, timezone: e.target.value })} />
                <TextField select label="Default language" value={settings.language} onChange={(e) => setSettings({ ...settings, language: e.target.value })}>
                  <MenuItem value="en">English</MenuItem>
                  <MenuItem value="fr">French</MenuItem>
                </TextField>
                <Button variant="contained" onClick={() => void save()}>
                  Save changes
                </Button>
                <SettingsOperatorSections
                  settings={settings}
                  modelOptions={providerRows.map((row) => data?.providers?.[row.id]?.default_model || row.id).filter(Boolean)}
                  onSaved={() => void mutate()}
                />
              </>
            ) : null}

            {tab === 1 ? (
              <LlmProvidersPanel
                providerRows={providerRows}
                providers={data?.providers}
                customProviders={customProviders}
                busy={providerBusy}
                onConfigureBuiltin={openBuiltinDialog}
                onRemoveBuiltin={removeBuiltinProvider}
                onMakeDefault={makeDefault}
                onConfigureCustom={openCustomDialog}
                onRemoveCustom={removeCustomProvider}
              />
            ) : null}

            {tab === 2 ? (
              <>
                <TextField
                  type="number"
                  label="Max tool iterations per turn"
                  value={settings.max_tool_iterations}
                  onChange={(e) => setSettings({ ...settings, max_tool_iterations: Number(e.target.value) })}
                />
                <Box>
                  <Typography variant="body2">Context compression threshold (tokens)</Typography>
                  <Slider
                    min={10000}
                    max={120000}
                    step={5000}
                    value={settings.context_compression_threshold}
                    onChange={(_, value) => setSettings({ ...settings, context_compression_threshold: value as number })}
                  />
                </Box>
                <Typography variant="subtitle2" sx={{ mt: 1 }}>
                  Provider modules
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={Boolean(settings.rtk_compression_enabled)}
                      onChange={(e) => setSettings({ ...settings, rtk_compression_enabled: e.target.checked })}
                    />
                  }
                  label="RTK token compression"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={Boolean(settings.caveman_compression_enabled)}
                      onChange={(e) => setSettings({ ...settings, caveman_compression_enabled: e.target.checked })}
                    />
                  }
                  label="Caveman compression"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.guardrails_pii_enabled !== false}
                      onChange={(e) => setSettings({ ...settings, guardrails_pii_enabled: e.target.checked })}
                    />
                  }
                  label="PII masking guardrail"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.guardrails_injection_enabled !== false}
                      onChange={(e) => setSettings({ ...settings, guardrails_injection_enabled: e.target.checked })}
                    />
                  }
                  label="Prompt injection guardrail"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={Boolean(settings.semantic_cache_enabled)}
                      onChange={(e) => setSettings({ ...settings, semantic_cache_enabled: e.target.checked })}
                    />
                  }
                  label="Semantic prompt cache"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={Boolean(settings.combo_routing_enabled)}
                      onChange={(e) => setSettings({ ...settings, combo_routing_enabled: e.target.checked })}
                    />
                  }
                  label="Combo provider routing"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.mutation_engine_enabled}
                      onChange={(e) => setSettings({ ...settings, mutation_engine_enabled: e.target.checked })}
                    />
                  }
                  label="Enable Mutation engine"
                />
                <TextField
                  type="number"
                  label="Mutation sandbox timeout (seconds)"
                  value={settings.mutation_sandbox_timeout}
                  onChange={(e) => setSettings({ ...settings, mutation_sandbox_timeout: Number(e.target.value) })}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.auto_approve_owner_mutations}
                      onChange={(e) => setSettings({ ...settings, auto_approve_owner_mutations: e.target.checked })}
                    />
                  }
                  label="Auto-approve mutations from owner only"
                />
                <Button variant="contained" onClick={() => void save()}>
                  Save changes
                </Button>
              </>
            ) : null}

            {tab === 3 ? (
              <>
                <TextField
                  label="PostgreSQL connection string"
                  type="password"
                  value={settings.postgres_url}
                  onChange={(e) => setSettings({ ...settings, postgres_url: e.target.value })}
                />
                <TextField
                  label="Redis connection string"
                  type="password"
                  value={settings.redis_url}
                  onChange={(e) => setSettings({ ...settings, redis_url: e.target.value })}
                />
                <TextField
                  select
                  label="Vector store engine"
                  value={settings.vector_store_engine}
                  onChange={(e) => setSettings({ ...settings, vector_store_engine: e.target.value })}
                >
                  <MenuItem value="pgvector">pgvector</MenuItem>
                  <MenuItem value="weaviate">weaviate</MenuItem>
                  <MenuItem value="qdrant">qdrant</MenuItem>
                </TextField>
                <TextField
                  type="number"
                  label="Max memory documents"
                  value={settings.max_memory_documents}
                  onChange={(e) => setSettings({ ...settings, max_memory_documents: Number(e.target.value) })}
                />
                <Button variant="contained" onClick={() => void save()}>
                  Save changes
                </Button>
              </>
            ) : null}

            {tab === 4 && data?.governance_enabled ? (
              <>
                <TextField
                  label="Governance license key"
                  type="password"
                  value={settings.governance_config?.license_key || ""}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      governance_config: {
                        ...settings.governance_config,
                        license_key: e.target.value,
                        audit_policy_url: settings.governance_config?.audit_policy_url || "",
                        provider_endpoint: settings.governance_config?.provider_endpoint || "",
                      },
                    })
                  }
                />
                <TextField
                  label="Audit policy URL"
                  value={settings.governance_config?.audit_policy_url || ""}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      governance_config: {
                        ...settings.governance_config,
                        license_key: settings.governance_config?.license_key || "",
                        audit_policy_url: e.target.value,
                        provider_endpoint: settings.governance_config?.provider_endpoint || "",
                      },
                    })
                  }
                />
                <TextField
                  label="Provider endpoint"
                  value={settings.governance_config?.provider_endpoint || ""}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      governance_config: {
                        ...settings.governance_config,
                        license_key: settings.governance_config?.license_key || "",
                        audit_policy_url: settings.governance_config?.audit_policy_url || "",
                        provider_endpoint: e.target.value,
                      },
                    })
                  }
                />
                <Button variant="outlined" onClick={() => setTestMessage("Governance connection test queued")}>
                  Test connection
                </Button>
                <Typography variant="body2">
                  Configure an external governance provider via Settings &gt; Governance or your active extension manifest.
                </Typography>
                <Button variant="contained" onClick={() => void save()}>
                  Save changes
                </Button>
              </>
            ) : null}
          </Box>
        </BlankCard>
      </Box>

      {testMessage ? (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          {testMessage}
        </Typography>
      ) : null}

      <Dialog open={Boolean(providerDialog)} onClose={() => setProviderDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure provider</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <DialogContentText>
            Leave API key blank to keep the existing key. Saving writes to your environment file.
          </DialogContentText>
          <TextField label="API key" type="password" value={providerKey} onChange={(e) => setProviderKey(e.target.value)} />
          <TextField label="Default model" value={providerModel} onChange={(e) => setProviderModel(e.target.value)} />
        </DialogContent>
        <DialogActions>
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
          <DialogContentText>
            Use an OpenAI-compatible base URL, for example `http://localhost:11434/v1` for Ollama or your hosted endpoint.
          </DialogContentText>
          <TextField label="Display name" value={customName} onChange={(e) => setCustomName(e.target.value)} fullWidth />
          <TextField label="Base URL" value={customBaseUrl} onChange={(e) => setCustomBaseUrl(e.target.value)} fullWidth />
          <TextField
            label="API key"
            type="password"
            value={customApiKey}
            onChange={(e) => setCustomApiKey(e.target.value)}
            helperText={editingCustomId ? "Leave blank to keep the existing key." : "Optional for local endpoints."}
            fullWidth
          />
          <TextField label="Default model" value={customModel} onChange={(e) => setCustomModel(e.target.value)} fullWidth />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCustomDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => {
              if (!editingCustomId) return;
              void testCustomProviderConnection(editingCustomId).then((result) => setTestMessage(result.message));
            }}
            disabled={!editingCustomId}
          >
            Test connection
          </Button>
          <Button
            variant="contained"
            disabled={providerBusy || !customName.trim() || !customBaseUrl.trim()}
            onClick={() => {
              setProviderBusy(true);
              const payload = {
                name: customName.trim(),
                base_url: customBaseUrl.trim(),
                api_key: customApiKey.trim() || undefined,
                default_model: customModel.trim() || undefined,
              };
              const action = editingCustomId
                ? updateCustomProvider(editingCustomId, payload)
                : createCustomProvider(payload);
              void action
                .then(() => {
                  setCustomDialogOpen(false);
                  return mutate();
                })
                .catch((err: unknown) => {
                  setTestMessage(err instanceof Error ? err.message : "Could not save custom provider");
                })
                .finally(() => setProviderBusy(false));
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </PageContainer>
  );
}

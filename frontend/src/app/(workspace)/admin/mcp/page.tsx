"use client";

import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ExtensionIcon from "@mui/icons-material/Extension";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import * as React from "react";
import NextLink from "next/link";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import PageHeader from "@/components/ui/PageHeader";
import {
  addMcpFromCatalog,
  addMcpServer,
  deleteMcpServer,
  fetchAutoSpawnStatus,
  fetchMcpCatalog,
  fetchMcpServers,
  fetchMcpVaultSecretKeys,
  fetchOptionalMcpCatalogEntries,
  installOptionalMcpEntry,
  setAutoMcpSpawnEnabled,
  setMcpServerEnabled,
  startMcpOAuth,
  testMcpServer,
  updateMcpServer,
  type McpCatalogEntry,
  type McpServer,
  type McpServerInput,
  type OptionalMcpCatalogEntry,
} from "@/lib/admin-api";
import { docsPageUrl } from "@/lib/docs-url";

type DialogState = {
  open: boolean;
  editing: McpServer | null;
  transport: "stdio" | "http";
  name: string;
  command: string;
  args: string;
  url: string;
  sseOverride: boolean;
  envPairs: Array<{ key: string; value: string }>;
};

type CatalogCredDialog = {
  open: boolean;
  entry: McpCatalogEntry | null;
  env: Record<string, string>;
  vaultEnv: Record<string, string>;
};

const EMPTY_DIALOG: DialogState = {
  open: false,
  editing: null,
  transport: "stdio",
  name: "",
  command: "",
  args: "",
  url: "",
  sseOverride: false,
  envPairs: [],
};

const EMPTY_CATALOG_DIALOG: CatalogCredDialog = {
  open: false,
  entry: null,
  env: {},
  vaultEnv: {},
};

type N8nInstallDialogState = {
  open: boolean;
  env: Record<string, string>;
};

const EMPTY_N8N_INSTALL_DIALOG: N8nInstallDialogState = {
  open: false,
  env: {},
};

function manifestDocsHref(docsUrl?: string | null): string | null {
  if (!docsUrl) {
    return null;
  }
  const stripped = docsUrl.replace(/^\/docs\/?/, "").replace(/^\//, "").replace(/\/$/, "");
  return docsPageUrl(stripped);
}

function n8nBridgeStatus(entry: OptionalMcpCatalogEntry | undefined): {
  label: string;
  color: "default" | "success" | "warning";
} {
  if (!entry?.installed) {
    return { label: "Not installed", color: "default" };
  }
  if (entry.enabled) {
    return { label: "Installed and enabled", color: "success" };
  }
  return { label: "Installed (disabled)", color: "warning" };
}

const CREDENTIAL_HINTS: Record<string, string> = {
  GITHUB_PERSONAL_ACCESS_TOKEN: "Get your token at github.com/settings/tokens",
  NOTION_TOKEN: "Create at notion.so/my-integrations; share pages with the integration",
  TRELLO_API_KEY: "Get from trello.com/power-ups/admin",
  TRELLO_TOKEN: "Generate token from the same Power-Up admin page",
  N8N_BASE_URL: "Default http://127.0.0.1:5678 when using local Docker n8n",
  N8N_API_KEY: "Generate under n8n Settings → API (see n8n sidecar docs)",
};

function connectionStatusLabel(status: McpServer["connection_status"]): string {
  switch (status) {
    case "connected":
      return "Connected";
    case "needs_oauth":
      return "Needs OAuth";
    case "needs_credentials":
      return "Needs credentials";
    case "error":
      return "Error";
    case "disabled":
      return "Disabled";
    default:
      return "Unknown";
  }
}

function connectionStatusColor(
  status: McpServer["connection_status"],
): "default" | "success" | "warning" | "error" {
  switch (status) {
    case "connected":
      return "success";
    case "needs_oauth":
    case "needs_credentials":
      return "warning";
    case "error":
      return "error";
    default:
      return "default";
  }
}

function toolNamesFromResult(
  tools: Array<string | { name: string; description?: string }> | undefined,
): string[] {
  return (tools || []).map((tool) => (typeof tool === "string" ? tool : tool.name));
}

function formatToolList(tools: string[]): React.ReactNode {
  const visible = tools.slice(0, 8);
  const extra = tools.length - visible.length;
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
      {visible.map((tool) => (
        <Chip key={tool} size="small" label={tool} variant="outlined" />
      ))}
      {extra > 0 ? <Chip size="small" label={`+${extra} more`} variant="outlined" /> : null}
    </Box>
  );
}

export default function McpAdminPage() {
  const [tab, setTab] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [dialog, setDialog] = React.useState<DialogState>(EMPTY_DIALOG);
  const [catalogDialog, setCatalogDialog] = React.useState<CatalogCredDialog>(EMPTY_CATALOG_DIALOG);
  const [saving, setSaving] = React.useState(false);
  const [catalogAdding, setCatalogAdding] = React.useState<string | null>(null);
  const [toolsByServer, setToolsByServer] = React.useState<Record<string, string[]>>({});
  const [testing, setTesting] = React.useState<string | null>(null);
  const [spawnToggling, setSpawnToggling] = React.useState(false);
  const [highlightServer, setHighlightServer] = React.useState<string | null>(null);
  const [oauthConnecting, setOauthConnecting] = React.useState<string | null>(null);
  const [oauthPolling, setOauthPolling] = React.useState<string | null>(null);
  const [n8nInstallDialog, setN8nInstallDialog] = React.useState<N8nInstallDialogState>(
    EMPTY_N8N_INSTALL_DIALOG,
  );
  const [n8nInstalling, setN8nInstalling] = React.useState(false);

  const {
    data: servers = [],
    isLoading: loading,
    mutate: mutateServers,
  } = useSWR("mcp-servers", fetchMcpServers, {
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Failed to load MCP servers");
    },
  });

  const { data: catalog = [], isLoading: catalogLoading } = useSWR("mcp-catalog", fetchMcpCatalog, {
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Failed to load MCP catalog");
    },
  });

  const { data: optionalCatalogEntries = [], mutate: mutateOptionalCatalog } = useSWR(
    "mcp-optional-catalog",
    fetchOptionalMcpCatalogEntries,
    { shouldRetryOnError: false },
  );

  const { data: autoSpawnStatus, mutate: mutateAutoSpawn } = useSWR(
    "mcp-auto-spawn-status",
    fetchAutoSpawnStatus,
  );

  const { data: vaultKeys = [] } = useSWR(
    catalogDialog.open ? "mcp-vault-keys" : null,
    fetchMcpVaultSecretKeys,
    { shouldRetryOnError: false },
  );

  React.useEffect(() => {
    if (!oauthPolling) {
      return undefined;
    }
    let ticks = 0;
    const timer = window.setInterval(() => {
      ticks += 1;
      void mutateServers().then((data) => {
        const server = (data || servers).find((item) => item.name === oauthPolling);
        if (server?.oauth_connected) {
          setOauthPolling(null);
          setSuccess(`${oauthPolling} connected via OAuth.`);
        }
      });
      if (ticks >= 20) {
        setOauthPolling(null);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [oauthPolling, mutateServers, servers]);

  const serverNames = React.useMemo(() => new Set(servers.map((s) => s.name)), [servers]);

  const n8nCatalogEntry = React.useMemo(
    () => optionalCatalogEntries.find((entry) => entry.name === "n8n"),
    [optionalCatalogEntries],
  );

  const n8nDocsHref =
    manifestDocsHref(n8nCatalogEntry?.docs_url) ?? docsPageUrl("integrations/n8n-sidecar");
  const n8nImportHref = docsPageUrl("features/migration") + "#from-n8n";

  React.useEffect(() => {
    setToolsByServer((prev) => {
      const next = { ...prev };
      for (const server of servers) {
        if (server.tools?.length && !next[server.name]) {
          next[server.name] = server.tools;
        }
      }
      return next;
    });
  }, [servers]);

  const openAddDialog = () => {
    setDialog({ ...EMPTY_DIALOG, open: true });
  };

  const openEditDialog = (server: McpServer) => {
    const isStdio = server.transport === "stdio" || Boolean(server.command);
    setDialog({
      open: true,
      editing: server,
      transport: isStdio ? "stdio" : "http",
      name: server.name,
      command: server.command || "",
      args: (server.args || []).join(", "),
      url: server.url || "",
      sseOverride: server.transport === "sse",
      envPairs: Object.keys(server.env || {}).map((key) => ({
        key,
        value: "***",
      })),
    });
  };

  const closeDialog = () => setDialog(EMPTY_DIALOG);

  const updateDialog = (patch: Partial<DialogState>) => {
    setDialog((prev) => ({ ...prev, ...patch }));
  };

  const addEnvPair = () => {
    setDialog((prev) => ({
      ...prev,
      envPairs: [...prev.envPairs, { key: "", value: "" }],
    }));
  };

  const removeEnvPair = (index: number) => {
    setDialog((prev) => ({
      ...prev,
      envPairs: prev.envPairs.filter((_, i) => i !== index),
    }));
  };

  const validateDialog = (): string | null => {
    if (!dialog.name.trim()) {
      return "Name is required.";
    }
    if (dialog.transport === "stdio") {
      if (!dialog.command.trim()) {
        return "Command is required for stdio servers.";
      }
    } else if (!/^https?:\/\//i.test(dialog.url.trim())) {
      return "URL must start with http:// or https://.";
    }
    return null;
  };

  const buildPayload = (): McpServerInput => {
    const env: Record<string, string> = {};
    for (const pair of dialog.envPairs) {
      const key = pair.key.trim();
      if (!key) {
        continue;
      }
      if (dialog.editing && pair.value === "***") {
        env[key] = "***";
      } else if (pair.value) {
        env[key] = pair.value;
      }
    }

    const body: McpServerInput = {
      name: dialog.name.trim(),
      env,
    };

    if (dialog.transport === "stdio") {
      body.command = dialog.command.trim();
      body.args = dialog.args
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
    } else {
      body.url = dialog.url.trim();
      if (dialog.sseOverride) {
        body.transport = "sse";
      }
    }

    return body;
  };

  const handleSave = async () => {
    const validationError = validateDialog();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const body = buildPayload();
      if (dialog.editing) {
        await updateMcpServer(dialog.editing.name, body);
      } else {
        await addMcpServer(body);
      }
      closeDialog();
      await mutateServers();
      setSuccess(dialog.editing ? "Server updated." : "Server added.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save server");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (serverName: string) => {
    setTesting(serverName);
    setError(null);
    try {
      const result = await testMcpServer(serverName);
      if (!result.ok) {
        setError(result.error || "Connection test failed");
        return;
      }
      setToolsByServer((prev) => ({
        ...prev,
        [serverName]: toolNamesFromResult(result.tools),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection test failed");
    } finally {
      setTesting(null);
    }
  };

  const handleToggle = async (server: McpServer, enabled: boolean) => {
    setError(null);
    void mutateServers(
      servers.map((item) => (item.name === server.name ? { ...item, enabled } : item)),
      false,
    );
    try {
      await setMcpServerEnabled(server.name, enabled);
      await mutateServers();
    } catch (err) {
      await mutateServers();
      setError(err instanceof Error ? err.message : "Failed to update server");
    }
  };

  const handleAutoSpawnToggle = async (enabled: boolean) => {
    if (autoSpawnStatus?.env_locked) {
      return;
    }
    setSpawnToggling(true);
    setError(null);
    setSuccess(null);
    try {
      const next = await setAutoMcpSpawnEnabled(enabled);
      await mutateAutoSpawn(next, false);
      setSuccess(enabled ? "Auto-spawn enabled." : "Auto-spawn disabled.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update auto-spawn settings");
    } finally {
      setSpawnToggling(false);
    }
  };

  const handleDelete = async (serverName: string) => {
    if (!window.confirm(`Delete MCP server "${serverName}"?`)) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await deleteMcpServer(serverName);
      await mutateServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete server");
    }
  };

  const finishCatalogAdd = async (
    entry: McpCatalogEntry,
    env?: Record<string, string>,
    vault_env?: Record<string, string>,
  ) => {
    setCatalogAdding(entry.key);
    setError(null);
    setSuccess(null);
    try {
      await addMcpFromCatalog(entry.key, { env, vault_env });
      await mutateServers();
      setCatalogDialog(EMPTY_CATALOG_DIALOG);
      setTab(0);
      setHighlightServer(entry.key);
      if (entry.auth_type === "oauth") {
        setSuccess("Server added. Click Connect to sign in with Notion.");
      } else if (entry.homepage) {
        setSuccess(
          `${entry.label} added. See the setup guide, then use List tools to verify the connection.`,
        );
      } else {
        setSuccess(`${entry.label} added. Restart Keprix to activate new tools.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add from catalog");
    } finally {
      setCatalogAdding(null);
    }
  };

  const handleCatalogAdd = (entry: McpCatalogEntry) => {
    if (serverNames.has(entry.key)) {
      return;
    }
    if (entry.required_env.length === 0) {
      void finishCatalogAdd(entry);
      return;
    }
    const env: Record<string, string> = {};
    const vaultEnv: Record<string, string> = {};
    for (const key of entry.required_env) {
      env[key] = "";
      vaultEnv[key] = "";
    }
    setCatalogDialog({ open: true, entry, env, vaultEnv });
  };

  const handleOAuthConnect = async (serverName: string) => {
    setOauthConnecting(serverName);
    setError(null);
    setSuccess(null);
    try {
      const result = await startMcpOAuth(serverName);
      if (result.ok && result.oauth_connected) {
        await mutateServers();
        setSuccess(result.message || "Already connected.");
        return;
      }
      if (result.authorization_url) {
        window.open(result.authorization_url, "_blank", "noopener,noreferrer");
        setOauthPolling(serverName);
        setSuccess("Complete sign-in in the browser tab. This page will refresh when connected.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start OAuth");
    } finally {
      setOauthConnecting(null);
    }
  };

  const handleCatalogCredSave = async () => {
    const entry = catalogDialog.entry;
    if (!entry) {
      return;
    }
    const env: Record<string, string> = {};
    const vault_env: Record<string, string> = {};
    for (const key of entry.required_env) {
      const vaultId = catalogDialog.vaultEnv[key]?.trim();
      if (vaultId) {
        vault_env[key] = vaultId;
        continue;
      }
      const value = catalogDialog.env[key]?.trim();
      if (!value) {
        setError(`${key} is required (enter a value or pick from Vault).`);
        return;
      }
      env[key] = value;
    }
    await finishCatalogAdd(entry, env, Object.keys(vault_env).length ? vault_env : undefined);
  };

  const openN8nInstallDialog = () => {
    if (n8nCatalogEntry?.installed || serverNames.has("n8n")) {
      setTab(0);
      setHighlightServer("n8n");
      return;
    }
    const env: Record<string, string> = {};
    for (const spec of n8nCatalogEntry?.required_env ?? []) {
      env[spec.name] = spec.name === "N8N_BASE_URL" ? "http://127.0.0.1:5678" : "";
    }
    setN8nInstallDialog({ open: true, env });
  };

  const handleN8nInstallSave = async () => {
    if (!n8nCatalogEntry) {
      return;
    }
    for (const spec of n8nCatalogEntry.required_env) {
      if (spec.required && !n8nInstallDialog.env[spec.name]?.trim()) {
        setError(`${spec.name} is required.`);
        return;
      }
    }
    setN8nInstalling(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await installOptionalMcpEntry("n8n", { env: n8nInstallDialog.env });
      await mutateOptionalCatalog();
      await mutateServers();
      setN8nInstallDialog(EMPTY_N8N_INSTALL_DIALOG);
      setTab(0);
      setHighlightServer("n8n");
      if (result.background) {
        setSuccess(
          "n8n MCP install started in the background (git clone). Check action logs if it takes more than a minute.",
        );
      } else {
        setSuccess("n8n MCP installed. Start a new chat session to load n8n tools.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install n8n MCP");
    } finally {
      setN8nInstalling(false);
    }
  };

  const n8nStatus = n8nBridgeStatus(n8nCatalogEntry);

  return (
    <Box>
      <PageHeader
        title="MCP Servers"
        description="Connect external tool servers."
        breadcrumbs={[
          { label: "Admin", href: "/admin/mcp" },
          { label: "MCP Servers" },
        ]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component={NextLink} href="/integrations" variant="outlined">
              Marketplace view
            </Button>
            {tab === 0 ? (
              <Button variant="contained" startIcon={<AddIcon />} onClick={openAddDialog}>
                Add server
              </Button>
            ) : null}
          </Stack>
        }
      />

      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        <Tab label="My servers" />
        <Tab label="Browse catalog" />
      </Tabs>

      <Alert severity="info" sx={{ mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Also available without MCP
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Notion and Trello also work via bundled skills (terminal/curl) or by indexing Notion pages
          for RAG search when you do not need live MCP tools on every message.
        </Typography>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          <Button component={NextLink} href="/skills" size="small" variant="outlined">
            Skills hub (notion, trello)
          </Button>
          <Button
            component={NextLink}
            href="/rag-pipeline?source=notion"
            size="small"
            variant="outlined"
          >
            Notion RAG indexing
          </Button>
        </Stack>
      </Alert>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            alignItems={{ md: "flex-start" }}
            justifyContent="space-between"
          >
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
                <Typography variant="h6">n8n workflow bridge</Typography>
                <Chip size="small" label={n8nStatus.label} color={n8nStatus.color} variant="outlined" />
                {n8nCatalogEntry?.category ? (
                  <Chip size="small" label={n8nCatalogEntry.category} variant="outlined" />
                ) : null}
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                {n8nCatalogEntry?.description ??
                  "Manage and inspect n8n workflows from Keprix via a stdio MCP sidecar (no n8n nodes ported)."}
              </Typography>
              {n8nCatalogEntry?.default_tools?.length ? (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                  Default tools (read-mostly): {n8nCatalogEntry.default_tools.join(", ")}. Mutating tools are
                  opt-in at install.
                </Typography>
              ) : null}
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                <Button
                  component={NextLink}
                  href={n8nDocsHref}
                  size="small"
                  variant="text"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Sidecar docs
                </Button>
                <Button
                  component={NextLink}
                  href={n8nImportHref}
                  size="small"
                  variant="text"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Import workflow JSON
                </Button>
              </Stack>
            </Box>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ flexShrink: 0 }}>
              {n8nCatalogEntry?.installed || serverNames.has("n8n") ? (
                <Button size="small" variant="outlined" onClick={() => openN8nInstallDialog()}>
                  View in My servers
                </Button>
              ) : (
                <Button
                  size="small"
                  variant="contained"
                  disabled={!n8nCatalogEntry || n8nInstalling}
                  onClick={() => openN8nInstallDialog()}
                >
                  {n8nInstalling ? "Installing..." : "Install n8n MCP"}
                </Button>
              )}
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      {success ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      ) : null}

      {tab === 0 ? (
        <>
          {autoSpawnStatus ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 2,
                  flexWrap: "wrap",
                  alignItems: "flex-start",
                }}
              >
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  {autoSpawnStatus.enabled ? (
                    <>
                      <strong>Auto-spawn: Enabled</strong>
                      {"; "}
                      {autoSpawnStatus.auto_spawned_servers.length}{" "}
                      {autoSpawnStatus.auto_spawned_servers.length === 1
                        ? "server added automatically"
                        : "servers added automatically"}
                      . When auto-spawn is on, the agent can add MCPs from the catalog during a
                      task.
                    </>
                  ) : (
                    <>
                      <strong>Auto-spawn: Off</strong>
                      {"; "}
                      When off, the agent cannot add MCPs automatically during a task.
                    </>
                  )}
                  {autoSpawnStatus.env_locked ? (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Controlled by <code>KEPRIX_AUTO_MCP_SPAWN</code> in the environment. Unset
                      that variable to toggle from this page or set{" "}
                      <code>mcp.auto_spawn_enabled</code> in config.yaml.
                    </Typography>
                  ) : (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Setting is stored in config.yaml (
                      {autoSpawnStatus.source === "config" ? "config" : "environment"}).
                    </Typography>
                  )}
                </Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoSpawnStatus.enabled}
                      disabled={autoSpawnStatus.env_locked || spawnToggling}
                      onChange={(_, checked) => void handleAutoSpawnToggle(checked)}
                    />
                  }
                  label={autoSpawnStatus.enabled ? "On" : "Off"}
                />
              </Box>
            </Alert>
          ) : null}
          {loading ? (
          <SkeletonList rows={4} rowHeight={88} />
        ) : servers.length === 0 ? (
          <EmptyState
            title="No MCP servers configured"
            description="Add stdio or HTTP/SSE MCP servers, or browse the catalog for one-click installs."
            icon={<ExtensionIcon sx={{ fontSize: 48 }} />}
            actionLabel="Add server"
            onAction={openAddDialog}
          />
        ) : (
          <Stack spacing={1.5}>
            {servers.map((server) => {
              const tools = toolsByServer[server.name] || server.tools || [];
              const status = server.connection_status;
              const statusChip =
                status && status !== "disabled" ? (
                  server.connection_error && status === "error" ? (
                    <Tooltip title={server.connection_error}>
                      <Chip
                        size="small"
                        color={connectionStatusColor(status)}
                        label={connectionStatusLabel(status)}
                      />
                    </Tooltip>
                  ) : (
                    <Chip
                      size="small"
                      color={connectionStatusColor(status)}
                      label={connectionStatusLabel(status)}
                    />
                  )
                ) : null;
              return (
                <Card
                  key={server.name}
                  variant="outlined"
                  sx={
                    highlightServer === server.name
                      ? { borderColor: "primary.main", borderWidth: 2 }
                      : undefined
                  }
                >
                  <CardContent sx={{ display: "grid", gap: 1.5 }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 2,
                        flexWrap: "wrap",
                        alignItems: "flex-start",
                      }}
                    >
                      <Box sx={{ minWidth: 0, flex: 1 }}>
                        <Typography variant="subtitle1" fontWeight={600}>
                          {server.name}
                        </Typography>
                        <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
                          <Chip size="small" label={server.transport} />
                          <Chip
                            size="small"
                            color={server.enabled ? "success" : "default"}
                            label={server.enabled ? "Enabled" : "Disabled"}
                          />
                          {statusChip}
                          {server.auto_spawned ? (
                            <Chip size="small" label="Auto-added" variant="outlined" />
                          ) : null}
                        </Stack>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          {server.transport === "stdio"
                            ? [server.command, ...(server.args || [])].filter(Boolean).join(" ")
                            : server.url || "No endpoint"}
                        </Typography>
                        {tools.length > 0 ? formatToolList(tools) : null}
                      </Box>
                      <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                        {status === "needs_oauth" ? (
                          <Button
                            size="small"
                            variant="contained"
                            disabled={oauthConnecting === server.name || oauthPolling === server.name}
                            onClick={() => void handleOAuthConnect(server.name)}
                          >
                            {oauthConnecting === server.name || oauthPolling === server.name
                              ? "Connecting..."
                              : "Connect"}
                          </Button>
                        ) : null}
                        {status === "needs_credentials" ? (
                          <Button size="small" variant="outlined" onClick={() => openEditDialog(server)}>
                            Add credentials
                          </Button>
                        ) : null}
                        {(server.name === "notion" || server.name === "notion-token") &&
                        status === "connected" ? (
                          <Button
                            size="small"
                            variant="outlined"
                            component={NextLink}
                            href="/rag-pipeline?source=notion"
                          >
                            Index for search
                          </Button>
                        ) : null}
                        <FormControlLabel
                          control={
                            <Switch
                              checked={server.enabled}
                              onChange={(_, checked) => void handleToggle(server, checked)}
                            />
                          }
                          label={server.enabled ? "On" : "Off"}
                        />
                        <Button
                          size="small"
                          variant="outlined"
                          disabled={testing === server.name}
                          onClick={() => void handleTest(server.name)}
                        >
                          {testing === server.name ? "Testing..." : "List tools"}
                        </Button>
                        <Button size="small" variant="outlined" onClick={() => openEditDialog(server)}>
                          Edit
                        </Button>
                        <IconButton
                          aria-label={`Delete ${server.name}`}
                          onClick={() => void handleDelete(server.name)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Stack>
                    </Box>
                  </CardContent>
                </Card>
              );
            })}
          </Stack>
        )}
        </>
      ) : catalogLoading ? (
        <SkeletonList rows={4} rowHeight={120} />
      ) : (
        <Box
          sx={{
            display: "grid",
            gap: 1.5,
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          }}
        >
          {catalog.map((entry) => {
            const alreadyAdded = serverNames.has(entry.key);
            const tags = entry.capability_tags.slice(0, 4);
            const extraTags = entry.capability_tags.length - tags.length;
            return (
              <Card key={entry.key} variant="outlined">
                <CardContent sx={{ display: "grid", gap: 1.25 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, alignItems: "flex-start" }}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {entry.label}
                    </Typography>
                    <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                      {entry.capability_tags.includes("productivity") ? (
                        <Chip size="small" label="Productivity" color="primary" variant="outlined" />
                      ) : null}
                      <Chip size="small" label={entry.transport} />
                      {entry.auth_type === "oauth" ? (
                        <Chip size="small" label="OAuth" variant="outlined" />
                      ) : null}
                    </Stack>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {entry.description}
                  </Typography>
                  <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                    {tags.map((tag) => (
                      <Chip key={tag} size="small" label={tag} variant="outlined" />
                    ))}
                    {extraTags > 0 ? (
                      <Chip size="small" label={`+${extraTags} more`} variant="outlined" />
                    ) : null}
                  </Stack>
                  {entry.required_env.length > 0 ? (
                    <Typography variant="caption" color="text.secondary">
                      Requires: {entry.required_env.join(", ")}
                    </Typography>
                  ) : null}
                  {entry.homepage ? (
                    <Link href={entry.homepage} target="_blank" rel="noopener noreferrer" variant="body2">
                      Documentation
                    </Link>
                  ) : null}
                  <Box>
                    <Button
                      size="small"
                      variant="contained"
                      disabled={alreadyAdded || catalogAdding === entry.key}
                      onClick={() => handleCatalogAdd(entry)}
                    >
                      {alreadyAdded
                        ? "Already added"
                        : catalogAdding === entry.key
                          ? "Adding..."
                          : "Add"}
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}

      <Dialog open={dialog.open} onClose={closeDialog} fullWidth maxWidth="sm">
        <DialogTitle>{dialog.editing ? "Edit MCP server" : "Add MCP server"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Transport
            </Typography>
            <ToggleButtonGroup
              exclusive
              size="small"
              value={dialog.transport}
              onChange={(_, value: "stdio" | "http" | null) => {
                if (value) {
                  updateDialog({ transport: value });
                }
              }}
            >
              <ToggleButton value="stdio">stdio</ToggleButton>
              <ToggleButton value="http">HTTP/SSE</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {dialog.transport === "stdio" ? (
            <>
              <TextField
                label="Command"
                required
                value={dialog.command}
                onChange={(e) => updateDialog({ command: e.target.value })}
                placeholder="npx"
              />
              <TextField
                label="Arguments"
                value={dialog.args}
                onChange={(e) => updateDialog({ args: e.target.value })}
                placeholder="-y, @modelcontextprotocol/server-filesystem, /tmp"
                helperText="Comma-separated"
              />
            </>
          ) : (
            <>
              <TextField
                label="URL"
                required
                value={dialog.url}
                onChange={(e) => updateDialog({ url: e.target.value })}
                placeholder="https://my-mcp-server.example.com/mcp"
              />
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                  Transport type
                </Typography>
                <RadioGroup
                  value={dialog.sseOverride ? "sse" : "auto"}
                  onChange={(e) => updateDialog({ sseOverride: e.target.value === "sse" })}
                >
                  <FormControlLabel value="auto" control={<Radio size="small" />} label="Auto (Streamable HTTP)" />
                  <FormControlLabel value="sse" control={<Radio size="small" />} label="SSE" />
                </RadioGroup>
              </Box>
            </>
          )}

          <TextField
            label="Name"
            required
            value={dialog.name}
            onChange={(e) => updateDialog({ name: e.target.value })}
          />

          <Box>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Environment variables
              </Typography>
              <Button size="small" onClick={addEnvPair}>
                + Add variable
              </Button>
            </Box>
            <Stack spacing={1}>
              {dialog.envPairs.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  No environment variables configured.
                </Typography>
              ) : (
                dialog.envPairs.map((pair, index) => (
                  <Stack key={`${pair.key}-${index}`} direction="row" spacing={1} alignItems="center">
                    <TextField
                      size="small"
                      label="KEY"
                      value={pair.key}
                      onChange={(e) => {
                        const envPairs = [...dialog.envPairs];
                        envPairs[index] = { ...envPairs[index], key: e.target.value };
                        updateDialog({ envPairs });
                      }}
                      sx={{ flex: 1 }}
                    />
                    <TextField
                      size="small"
                      label="VALUE"
                      type="password"
                      value={pair.value}
                      onChange={(e) => {
                        const envPairs = [...dialog.envPairs];
                        envPairs[index] = { ...envPairs[index], value: e.target.value };
                        updateDialog({ envPairs });
                      }}
                      sx={{ flex: 2 }}
                    />
                    <IconButton size="small" onClick={() => removeEnvPair(index)} aria-label="Remove variable">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                ))
              )}
            </Stack>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Cancel</Button>
          <Button variant="contained" disabled={saving} onClick={() => void handleSave()}>
            {saving ? "Saving..." : dialog.editing ? "Save" : "Add"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={catalogDialog.open}
        onClose={() => setCatalogDialog(EMPTY_CATALOG_DIALOG)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Add {catalogDialog.entry?.label}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            This server requires credentials to connect.
          </Typography>
          {catalogDialog.entry?.required_env.map((envKey) => (
            <Box key={envKey}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "flex-start" }}>
                <TextField
                  label={`${envKey} *`}
                  type="password"
                  fullWidth
                  disabled={Boolean(catalogDialog.vaultEnv[envKey])}
                  value={catalogDialog.env[envKey] || ""}
                  onChange={(e) =>
                    setCatalogDialog((prev) => ({
                      ...prev,
                      env: { ...prev.env, [envKey]: e.target.value },
                    }))
                  }
                  sx={{ flex: 1 }}
                />
                <TextField
                  select
                  label="From Vault"
                  size="small"
                  value={catalogDialog.vaultEnv[envKey] || ""}
                  onChange={(e) =>
                    setCatalogDialog((prev) => ({
                      ...prev,
                      vaultEnv: { ...prev.vaultEnv, [envKey]: e.target.value },
                      env: e.target.value ? { ...prev.env, [envKey]: "" } : prev.env,
                    }))
                  }
                  sx={{ minWidth: { sm: 200 }, width: { xs: "100%", sm: "auto" } }}
                >
                  <MenuItem value="">None</MenuItem>
                  {vaultKeys.map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.label}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>
              {CREDENTIAL_HINTS[envKey] ? (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                  {CREDENTIAL_HINTS[envKey]}
                </Typography>
              ) : null}
            </Box>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCatalogDialog(EMPTY_CATALOG_DIALOG)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={catalogAdding === catalogDialog.entry?.key}
            onClick={() => void handleCatalogCredSave()}
          >
            {catalogAdding ? "Adding..." : "Add server"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={n8nInstallDialog.open}
        onClose={() => setN8nInstallDialog(EMPTY_N8N_INSTALL_DIALOG)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Install n8n MCP</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Connect to a running n8n instance. Local Docker:
            {" "}
            <Typography component="span" variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
              docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
            </Typography>
          </Typography>
          {(n8nCatalogEntry?.required_env ?? []).map((spec) => (
            <Box key={spec.name}>
              <TextField
                label={`${spec.prompt}${spec.required ? " *" : ""}`}
                type={spec.name.includes("KEY") || spec.name.includes("TOKEN") ? "password" : "text"}
                fullWidth
                value={n8nInstallDialog.env[spec.name] ?? ""}
                onChange={(e) =>
                  setN8nInstallDialog((prev) => ({
                    ...prev,
                    env: { ...prev.env, [spec.name]: e.target.value },
                  }))
                }
              />
              {CREDENTIAL_HINTS[spec.name] ? (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                  {CREDENTIAL_HINTS[spec.name]}
                </Typography>
              ) : null}
            </Box>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setN8nInstallDialog(EMPTY_N8N_INSTALL_DIALOG)}>Cancel</Button>
          <Button variant="contained" disabled={n8nInstalling} onClick={() => void handleN8nInstallSave()}>
            {n8nInstalling ? "Installing..." : "Install"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

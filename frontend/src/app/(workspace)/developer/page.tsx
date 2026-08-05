"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import {
  IconApi,
  IconBook,
  IconCode,
  IconCopy,
  IconExternalLink,
  IconKey,
  IconPlayerPlay,
  IconWebhook,
} from "@tabler/icons-react";
import NextLink from "next/link";
import { useCallback, useMemo, useState } from "react";
import useSWR from "swr";
import StatCard from "@/components/admin/StatCard";
import DashboardCard from "@/components/cards/DashboardCard";
import ClientApprovalPanel from "@/components/security/ClientApprovalPanel";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonBlock, SkeletonChart, SkeletonTable } from "@/components/ui/loading";
import PageHeader from "@/components/ui/PageHeader";
import { billingGateFeatureName, isBillingGateError } from "@/lib/billing-api";
import { getBackendBaseUrl } from "@/lib/ce-api";
import {
  createDeveloperKey,
  createDeveloperWebhook,
  fetchDeveloperDashboard,
  revokeDeveloperKey,
  setDeveloperKeyEnabled,
  updateDeveloperKey,
  type CreateApiKeyPayload,
  type DeveloperApiKey,
  type UpdateApiKeyPayload,
} from "@/lib/developer-api";
import ApiKeyEditor from "@/components/developer/ApiKeyEditor";

type TabId = "overview" | "keys" | "webhooks" | "clients" | "code" | "monitor";

const RESOURCE_LINKS = [
  {
    title: "TypeScript SDK",
    description: "Agents, workflows, evals, and memory helpers.",
    href: "/developer/sdk",
    icon: IconCode,
  },
  {
    title: "OpenAPI explorer",
    description: "Try endpoints interactively against your instance.",
    href: "/api/docs",
    icon: IconBook,
  },
  {
    title: "Agent apps",
    description: "Register and run portable agent applications.",
    href: "/agent-apps",
    icon: IconPlayerPlay,
  },
  {
    title: "Module inventory",
    description: "Find built pages and API modules that are not exposed in navigation.",
    href: "/developer/module-inventory",
    icon: IconApi,
  },
];

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [value]);

  return (
    <Tooltip title={copied ? "Copied" : "Copy"}>
      <IconButton size="small" onClick={() => void copy()} aria-label="Copy to clipboard">
        <IconCopy size={16} stroke={1.75} />
      </IconButton>
    </Tooltip>
  );
}

function CodeBlock({ code }: { code: string }) {
  return (
    <Box
      sx={{
        position: "relative",
        p: 2,
        borderRadius: 1,
        bgcolor: "background.default",
        border: 1,
        borderColor: "divider",
        fontFamily: "monospace",
        fontSize: "0.75rem",
        lineHeight: 1.6,
        overflow: "auto",
        whiteSpace: "pre-wrap",
      }}
    >
      <Box sx={{ position: "absolute", top: 4, right: 4 }}>
        <CopyButton value={code} />
      </Box>
      {code}
    </Box>
  );
}

export default function DeveloperPage() {
  const [tab, setTab] = useState<TabId>("overview");
  const [snippetLang, setSnippetLang] = useState<"python" | "typescript" | "curl">("python");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const [keyDialogOpen, setKeyDialogOpen] = useState(false);
  const [keyEditorMode, setKeyEditorMode] = useState<"create" | "edit">("create");
  const [editingKey, setEditingKey] = useState<DeveloperApiKey | null>(null);
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [creatingKey, setCreatingKey] = useState(false);

  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookEvents, setWebhookEvents] = useState("chat.completed");
  const [webhookSecret, setWebhookSecret] = useState<string | null>(null);
  const [creatingWebhook, setCreatingWebhook] = useState(false);

  const { data, error, isLoading, mutate } = useSWR("developer-dashboard", fetchDeveloperDashboard);

  const base = getBackendBaseUrl();
  const openapiUrl = data?.openapi_url ? `${base}${data.openapi_url}` : `${base}/openapi.json`;

  const snippets = useMemo(
    () => ({
      python:
        data?.sdk_snippets?.python ||
        `from openai import OpenAI\nclient = OpenAI(api_key="kp_...", base_url="${base}/v1")`,
      typescript:
        data?.sdk_snippets?.typescript ||
        `import OpenAI from "openai";\nconst client = new OpenAI({ apiKey: process.env.KEPRIX_API_KEY, baseURL: "${base}/v1" });`,
      curl:
        data?.sdk_snippets?.curl ||
        `curl -X POST ${base}/v1/chat/completions \\\n  -H "Authorization: Bearer kp_..." \\\n  -H "Content-Type: application/json" \\\n  -d '{"model":"keprix","messages":[{"role":"user","content":"hello"}]}'`,
    }),
    [base, data?.sdk_snippets],
  );

  const activeKeys = (data?.api_keys || []).filter((key) => !key.revoked).length;
  const activeWebhooks = (data?.webhooks || []).filter((hook) => !hook.disabled).length;
  const errorCount = data?.recent_errors?.length ?? 0;
  const hasActiveKey = activeKeys > 0;

  const openCreateKey = () => {
    setKeyEditorMode("create");
    setEditingKey(null);
    setCreatedSecret(null);
    setKeyDialogOpen(true);
  };

  const openEditKey = (key: DeveloperApiKey) => {
    setKeyEditorMode("edit");
    setEditingKey(key);
    setCreatedSecret(null);
    setKeyDialogOpen(true);
  };

  const handleCreateKey = async (payload: CreateApiKeyPayload) => {
    setCreatingKey(true);
    setActionError(null);
    try {
      const created = await createDeveloperKey(payload);
      setCreatedSecret(created.secret);
      await mutate();
      setActionMessage(`API key "${created.name}" created. Copy the secret now; it will not be shown again.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to create key");
      throw err;
    } finally {
      setCreatingKey(false);
    }
  };

  const handleUpdateKey = async (keyId: string, payload: UpdateApiKeyPayload) => {
    setCreatingKey(true);
    setActionError(null);
    try {
      const updated = await updateDeveloperKey(keyId, payload);
      setKeyDialogOpen(false);
      await mutate();
      setActionMessage(`API key "${updated.name}" updated.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update key");
      throw err;
    } finally {
      setCreatingKey(false);
    }
  };

  const handleToggleKey = async (key: DeveloperApiKey, enabled: boolean) => {
    setActionError(null);
    try {
      await setDeveloperKeyEnabled(key.id, enabled);
      await mutate();
      setActionMessage(`${enabled ? "Enabled" : "Disabled"} key "${key.name}".`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update key");
    }
  };

  const handleRevokeKey = async (key: DeveloperApiKey) => {
    setActionError(null);
    try {
      await revokeDeveloperKey(key.id);
      await mutate();
      setActionMessage(`Revoked key "${key.name}".`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to revoke key");
    }
  };

  const handleCreateWebhook = async () => {
    setCreatingWebhook(true);
    setActionError(null);
    setWebhookSecret(null);
    try {
      const events = webhookEvents
        .split(",")
        .map((event) => event.trim())
        .filter(Boolean);
      const created = await createDeveloperWebhook({ url: webhookUrl.trim(), events });
      setWebhookSecret(created.signing_secret || null);
      setWebhookUrl("");
      await mutate();
      setActionMessage(created.note || "Webhook created.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to create webhook");
    } finally {
      setCreatingWebhook(false);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <PageHeader
        title="Developer Platform"
        description="Build on Keprix with API keys, webhooks, OpenAI-compatible endpoints, and SDKs."
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button
              component={NextLink}
              href="/developer/sdk"
              variant="outlined"
              size="small"
              startIcon={<IconCode size={16} stroke={1.75} />}
            >
              TypeScript SDK
            </Button>
            <Button
              component={NextLink}
              href="/api/docs"
              variant="contained"
              size="small"
              startIcon={<IconBook size={16} stroke={1.75} />}
            >
              API explorer
            </Button>
          </Stack>
        }
      />

      {data?.version ? (
        <Typography variant="caption" color="text.secondary">
          Keprix {data.version}
        </Typography>
      ) : null}

      {error ? (
        <Alert severity="error">{error instanceof Error ? error.message : "Failed to load dashboard"}</Alert>
      ) : null}
      {actionError ? (
        <Alert severity="error" onClose={() => setActionError(null)}>
          {isBillingGateError(actionError) ? (
            <>
              This feature requires <strong>{billingGateFeatureName(actionError) || "a higher plan"}</strong>.{" "}
              <Button component={NextLink} href="/settings/billing" size="small" sx={{ ml: 0.5 }}>
                View plans
              </Button>
            </>
          ) : (
            actionError
          )}
        </Alert>
      ) : null}
      {actionMessage ? (
        <Alert severity="success" onClose={() => setActionMessage(null)}>
          {actionMessage}
        </Alert>
      ) : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Active API keys" value={activeKeys} loading={isLoading} icon={<IconKey size={22} stroke={1.75} />} color="primary" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Webhooks" value={activeWebhooks} loading={isLoading} icon={<IconWebhook size={22} stroke={1.75} />} color="secondary" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Models" value={data?.models?.length ?? 0} loading={isLoading} icon={<IconApi size={22} stroke={1.75} />} color="info" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Recent errors"
            value={errorCount}
            loading={isLoading}
            icon={<IconApi size={22} stroke={1.75} />}
            color={errorCount > 0 ? "warning" : "success"}
          />
        </Grid>
      </Grid>

      <Tabs value={tab} onChange={(_, value: TabId) => setTab(value)} variant="scrollable" scrollButtons="auto">
        <Tab value="overview" label="Get started" />
        <Tab value="keys" label="API keys" />
        <Tab value="webhooks" label="Webhooks" />
        <Tab value="clients" label="Client approvals" />
        <Tab value="code" label="Code samples" />
        <Tab value="monitor" label="Usage and errors" />
      </Tabs>

      {tab === "clients" ? <ClientApprovalPanel /> : null}

      {tab === "overview" ? (
        <Stack spacing={2}>
          <DashboardCard title="Three steps to your first API call" subtitle="Everything you need is on this page">
            <Stack spacing={2}>
              <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                  1. Create an API key
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Generate a secret for programmatic access to chat, tools, and agent endpoints.
                </Typography>
                <Button variant="contained" size="small" onClick={openCreateKey}>
                  Create API key
                </Button>
              </Box>
              <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1, opacity: hasActiveKey ? 1 : 0.7 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                  2. Copy a code sample
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Use OpenAI-compatible clients pointed at your Keprix base URL.
                </Typography>
                <Button variant="outlined" size="small" onClick={() => setTab("code")} disabled={!hasActiveKey}>
                  View code samples
                </Button>
              </Box>
              <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                  3. Explore the API
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Open the interactive explorer or download the OpenAPI spec.
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Button component={NextLink} href="/api/docs" variant="outlined" size="small">
                    Open explorer
                  </Button>
                  <Button component="a" href={openapiUrl} target="_blank" rel="noreferrer" variant="text" size="small">
                    OpenAPI JSON
                  </Button>
                </Stack>
              </Box>
            </Stack>
          </DashboardCard>

          <Grid container spacing={2}>
            {RESOURCE_LINKS.map((link) => {
              const Icon = link.icon;
              return (
                <Grid key={link.href} size={{ xs: 12, md: 4 }}>
                  <DashboardCard
                    title={link.title}
                    subtitle={link.description}
                    action={
                      <Button component={NextLink} href={link.href} size="small" endIcon={<IconExternalLink size={14} />}>
                        Open
                      </Button>
                    }
                  >
                    <Icon size={28} stroke={1.5} style={{ opacity: 0.6 }} />
                  </DashboardCard>
                </Grid>
              );
            })}
          </Grid>

          <DashboardCard title="OpenAPI endpoint" subtitle="Use this as your client base URL for schema-driven tooling">
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Typography variant="body2" sx={{ fontFamily: "monospace", wordBreak: "break-all" }}>
                {openapiUrl}
              </Typography>
              <CopyButton value={openapiUrl} />
            </Stack>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
              {(data?.models || ["keprix"]).map((model) => (
                <Chip key={model} label={model} size="small" variant="outlined" />
              ))}
            </Stack>
          </DashboardCard>
        </Stack>
      ) : null}

      {tab === "keys" ? (
        <DashboardCard
          title="API keys"
          subtitle="Least-privilege keys for external apps. Secrets shown once."
          action={
            <Button variant="contained" size="small" onClick={openCreateKey}>
              + Create Key
            </Button>
          }
        >
          {isLoading ? (
            <SkeletonTable rows={4} columns={5} />
          ) : !data?.api_keys?.length ? (
            <EmptyState
              title="No API keys yet"
              description="Create a restricted key (chat-only by default) for scripts, SDKs, or other apps."
              icon={<IconKey size={40} stroke={1.5} />}
              actionLabel="Create API key"
              onAction={openCreateKey}
            />
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Key</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Expires</TableCell>
                  <TableCell>Enabled</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.api_keys.map((key) => (
                  <TableRow key={key.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {key.name}
                      </Typography>
                      {key.restrict_key === false ? (
                        <Typography variant="caption" color="warning.main">
                          Unrestricted
                        </Typography>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          Restricted
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                        {key.masked_key || `${key.key_prefix}...`}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {key.created_at ? key.created_at.slice(0, 10) : ";"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {key.expires_at ? key.expires_at.slice(0, 10) : "Never"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Switch
                        size="small"
                        checked={!key.revoked && key.enabled !== false}
                        disabled={key.revoked}
                        onChange={(e) => void handleToggleKey(key, e.target.checked)}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        <Button size="small" disabled={key.revoked} onClick={() => openEditKey(key)}>
                          Edit
                        </Button>
                        <Button
                          size="small"
                          color="inherit"
                          disabled={key.revoked}
                          onClick={() => void handleRevokeKey(key)}
                        >
                          Revoke
                        </Button>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DashboardCard>
      ) : null}

      {tab === "webhooks" ? (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 5 }}>
            <DashboardCard title="Create webhook" subtitle="Receive outbound events from Keprix">
              <Stack spacing={2}>
                <TextField
                  label="Endpoint URL"
                  value={webhookUrl}
                  onChange={(event) => setWebhookUrl(event.target.value)}
                  fullWidth
                  placeholder="https://example.com/webhooks/keprix"
                />
                <TextField
                  label="Events (comma-separated)"
                  value={webhookEvents}
                  onChange={(event) => setWebhookEvents(event.target.value)}
                  fullWidth
                  helperText="Example: chat.completed, tool.executed"
                />
                <Button
                  variant="contained"
                  disabled={creatingWebhook || !webhookUrl.trim()}
                  onClick={() => void handleCreateWebhook()}
                >
                  {creatingWebhook ? "Creating..." : "Create webhook"}
                </Button>
                {webhookSecret ? (
                  <Alert severity="warning">
                    Signing secret (copy now):{" "}
                    <Typography component="span" sx={{ fontFamily: "monospace" }}>
                      {webhookSecret}
                    </Typography>
                    <CopyButton value={webhookSecret} />
                  </Alert>
                ) : null}
              </Stack>
            </DashboardCard>
          </Grid>
          <Grid size={{ xs: 12, lg: 7 }}>
            <DashboardCard title="Registered webhooks" subtitle="Active outbound subscriptions">
              {isLoading ? (
                <SkeletonTable rows={4} columns={3} />
              ) : !data?.webhooks?.length ? (
                <Typography variant="body2" color="text.secondary">
                  No webhooks configured yet.
                </Typography>
              ) : (
                <Stack spacing={1.5}>
                  {data.webhooks.map((hook) => (
                    <Box
                      key={hook.id}
                      sx={{
                        p: 1.5,
                        border: 1,
                        borderColor: "divider",
                        borderRadius: 1,
                        bgcolor: "background.default",
                      }}
                    >
                      <Typography variant="body2" sx={{ fontFamily: "monospace", wordBreak: "break-all" }}>
                        {hook.url}
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                        {(hook.events || []).map((event) => (
                          <Chip key={event} label={event} size="small" variant="outlined" />
                        ))}
                        {hook.disabled ? <Chip label="Disabled" size="small" color="warning" /> : null}
                      </Stack>
                    </Box>
                  ))}
                </Stack>
              )}
            </DashboardCard>
          </Grid>
        </Grid>
      ) : null}

      {tab === "code" ? (
        <Stack spacing={2}>
          <DashboardCard title="Integration snippets" subtitle="OpenAI-compatible clients using your Keprix instance">
            <Tabs
              value={snippetLang}
              onChange={(_, value: "python" | "typescript" | "curl") => setSnippetLang(value)}
              sx={{ mb: 2 }}
            >
              <Tab value="python" label="Python" />
              <Tab value="typescript" label="TypeScript" />
              <Tab value="curl" label="cURL" />
            </Tabs>
            {isLoading ? <SkeletonBlock height={160} /> : <CodeBlock code={snippets[snippetLang]} />}
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
              Replace <code>kp_...</code> with a key from the API keys tab. Base URL: {base}/v1
            </Typography>
          </DashboardCard>
          <DashboardCard title="Agent app API" subtitle="Run installed apps from automation or scripts">
            <CodeBlock
              code={`curl -X POST ${base}/api/agent-apps/daily-standup/run \\
  -H "Authorization: Bearer kp_..." \\
  -H "Content-Type: application/json" \\
  -d '{"runner":"api","inputs":{"focus":"Ship billing"}}'`}
            />
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
              Per-app webhook URLs are created from the app detail Automate section. They POST to{" "}
              <code>{base}/api/public/agent-apps/hooks/&lt;token&gt;</code> without a session cookie.
            </Typography>
          </DashboardCard>
        </Stack>
      ) : null}

      {tab === "monitor" ? (
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <DashboardCard title="Usage by model" subtitle="Recent request totals">
                {isLoading ? (
                  <SkeletonChart height={120} />
                ) : !data?.usage?.by_model?.length ? (
                  <Typography variant="body2" color="text.secondary">
                    No usage recorded yet.
                  </Typography>
                ) : (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Model</TableCell>
                        <TableCell align="right">Total</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.usage.by_model.map((row) => (
                        <TableRow key={row.name}>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                              {row.name}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">{row.total}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </DashboardCard>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <DashboardCard title="Rate limits" subtitle="Per-route throttling rules">
                {isLoading ? (
                  <SkeletonChart height={120} />
                ) : (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Route</TableCell>
                        <TableCell>Limit</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(data?.rate_limits || {}).map(([name, value]) => (
                        <TableRow key={name}>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                              {name}
                            </Typography>
                          </TableCell>
                          <TableCell>{value}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </DashboardCard>
            </Grid>
          </Grid>

          <DashboardCard title="Enabled tools" subtitle="Toolsets available to api_server">
            {isLoading ? (
              <SkeletonBlock height={60} />
            ) : (
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {(data?.enabled_tools || []).map((tool) => (
                  <Chip key={tool} label={tool} size="small" variant="outlined" />
                ))}
                {!data?.enabled_tools?.length ? (
                  <Typography variant="body2" color="text.secondary">
                    No toolsets resolved.
                  </Typography>
                ) : null}
              </Stack>
            )}
          </DashboardCard>

          <DashboardCard title="Recent API errors" subtitle="Failed requests for debugging">
            {isLoading ? (
              <SkeletonTable rows={3} columns={3} />
            ) : !data?.recent_errors?.length ? (
              <Typography variant="body2" color="text.secondary">
                No recent API errors.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Path</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Message</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.recent_errors.map((entry, index) => (
                    <TableRow key={`${entry.path}-${index}`}>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                          {entry.path}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={String(entry.status_code)}
                          color={entry.status_code >= 500 ? "error" : "warning"}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {entry.error_message || "-"}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </DashboardCard>
        </Stack>
      ) : null}

      <ApiKeyEditor
        open={keyDialogOpen}
        mode={keyEditorMode}
        catalog={data?.scope_catalog || null}
        models={data?.models || ["keprix"]}
        initial={editingKey}
        createdSecret={createdSecret}
        saving={creatingKey}
        onClose={() => {
          setKeyDialogOpen(false);
          setCreatedSecret(null);
          setEditingKey(null);
        }}
        onCreate={handleCreateKey}
        onUpdate={handleUpdateKey}
      />
    </Box>
  );
}

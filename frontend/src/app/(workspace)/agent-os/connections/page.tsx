"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { AGENT_OS_HUB_HOME } from "@/components/agent-os/AgentOsSubnav";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/loading";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type Domain = { id: string; label: string; status: string; tools: string[]; service_account: boolean; integration_ref?: string | null };
type Suggestion = { domain: string; label: string; rationale: string; suggested_tools: string[] };

const STATUSES = ["planned", "configuring", "live", "n/a"];

export default function ConnectionsPage() {
  const [workspaceId, setWorkspaceId] = React.useState("personal-os");
  const [workspacePath, setWorkspacePath] = React.useState("");
  const [domains, setDomains] = React.useState<Domain[]>([]);
  const [suggestions, setSuggestions] = React.useState<Suggestion[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const parse = async <T,>(response: Response, fallback: string): Promise<T> => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(parseApiErrorMessage(payload, fallback));
    return payload as T;
  };

  const load = React.useCallback(async () => {
    const params = new URLSearchParams({ workspace_id: workspaceId || "personal-os" });
    if (workspacePath.trim()) params.set("workspace_path", workspacePath.trim());
    const payload = await parse<{ domains: Domain[] }>(await ceApi(`/api/agent-os/connections?${params}`), "Could not load connections");
    setDomains(payload.domains);
  }, [workspaceId, workspacePath]);

  React.useEffect(() => {
    setLoading(true);
    load()
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load connections"))
      .finally(() => setLoading(false));
  }, [load]);

  const init = async () => {
    setError(null);
    try {
      const payload = await parse<{ domains: Domain[] }>(
        await ceApi("/api/agent-os/connections/init-template", {
          method: "POST",
          body: JSON.stringify({ workspace_id: workspaceId, workspace_path: workspacePath.trim() || undefined }),
        }),
        "Could not initialize connections",
      );
      setDomains(payload.domains);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not initialize connections");
    }
  };

  const suggest = async () => {
    const payload = await parse<{ suggestions: Suggestion[] }>(
      await ceApi("/api/agent-os/connections/suggest-priority", {
        method: "POST",
        body: JSON.stringify({ workspace_id: workspaceId, workspace_path: workspacePath.trim() || undefined }),
      }),
      "Could not suggest priorities",
    );
    setSuggestions(payload.suggestions);
  };

  const update = async (domain: Domain, status: string) => {
    const payload = await parse<{ domains: Domain[] }>(
      await ceApi("/api/agent-os/connections", {
        method: "PUT",
        body: JSON.stringify({
          workspace_id: workspaceId,
          workspace_path: workspacePath.trim() || undefined,
          domain: domain.id,
          status,
          tools: domain.tools,
          integration_ref: domain.integration_ref,
          service_account: domain.service_account,
        }),
      }),
      "Could not update domain",
    );
    setDomains(payload.domains);
  };

  return (
    <Box>
      <PageHeader
        title="Connections"
        description="Day-2 domain matrix: planned tools and service accounts for your OS."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: AGENT_OS_HUB_HOME },
          { label: "Connections" },
        ]}
      />
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "flex-end" }}>
            <TextField label="Workspace id" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} size="small" />
            <TextField label="Workspace path" value={workspacePath} onChange={(event) => setWorkspacePath(event.target.value)} size="small" fullWidth />
            <Button variant="contained" onClick={() => void init()}>Init template</Button>
            <Button variant="outlined" onClick={() => void suggest()}>Suggest top 3</Button>
          </Stack>
        </CardContent>
      </Card>
      {error ? (
        <Box sx={{ mb: 2 }}>
          <ErrorState title="Connections error" message={error} onRetry={() => void load()} />
        </Box>
      ) : null}
      {suggestions.length ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          {suggestions.map((item) => `${item.label}: ${item.rationale}`).join(" ")}
        </Alert>
      ) : null}
      {loading ? <SkeletonBlock height={160} /> : null}
      {!loading && !domains.length && !error ? (
        <EmptyState
          title="No connection domains yet"
          description="Initialize the template to seed email, calendar, CRM, and other domains."
          actionLabel="Init template"
          onAction={() => void init()}
        />
      ) : null}
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 1fr" } }}>
        {domains.map((domain) => (
          <Card key={domain.id} variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="subtitle1">{domain.label}</Typography>
                <Chip label={domain.status} color={domain.status === "live" ? "success" : "default"} />
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Suggested tools: {domain.tools.length ? domain.tools.join(", ") : "none selected"}
              </Typography>
              <TextField select size="small" label="Status" value={domain.status} onChange={(event) => void update(domain, event.target.value)} fullWidth>
                {STATUSES.map((status) => <MenuItem key={status} value={status}>{status}</MenuItem>)}
              </TextField>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type SidecarProject = {
  project_key?: string;
  projectKey?: string;
  display_name?: string;
  displayName?: string;
  environment?: string;
  health?: string | { status?: string };
  kill_switch?: boolean;
  killSwitch?: boolean;
};

type ProjectsResponse = {
  projects?: SidecarProject[];
  items?: SidecarProject[];
};

type PairResponse = {
  pairing_code?: string;
  pairingCode?: string;
  expires_at?: string;
  expiresAt?: string;
  project_key?: string;
  scopes?: string[];
  jti?: string;
  access_token?: string;
};

const STARTER_MANIFEST = JSON.stringify(
  {
    contract_version: "1.0.0",
    project_key: "my-project",
    display_name: "My Project",
    deployment: "local-dev",
    environment: "local",
    base_url: "http://127.0.0.1:8080",
    auth: { profile: "bearer", vault_ref: "env:MY_PROJECT_TOKEN" },
    egress: { allow_loopback: true, allow_private_networks: false, allowed_hosts: [] },
    capabilities: [{ node: "summarise", version: "1.0.0", scopes: ["invoke:summarise"] }],
    memory: { mode: "ephemeral", retention_days: 0 },
    connectors: [],
    events: [],
  },
  null,
  2,
);

function projectKeyOf(p: SidecarProject): string {
  return p.project_key || p.projectKey || "";
}

function healthLabel(p: SidecarProject): string {
  if (typeof p.health === "string") return p.health;
  if (p.health && typeof p.health === "object" && p.health.status) return String(p.health.status);
  return "unknown";
}

async function fetchProjects(): Promise<SidecarProject[]> {
  const response = await ceApi("/sidecar/v1/projects");
  if (response.status === 404) return [];
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Failed to list projects (${response.status})`);
  }
  const body = (await response.json()) as ProjectsResponse | SidecarProject[];
  if (Array.isArray(body)) return body;
  return body.projects || body.items || [];
}

export default function SidecarsSettingsPage() {
  const { data, error, mutate, isLoading } = useSWR("sidecar-projects", fetchProjects);
  const [message, setMessage] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [pairProjectKey, setPairProjectKey] = React.useState("");
  const [pairScopes, setPairScopes] = React.useState("discover,invoke:summarise");
  const [pairResult, setPairResult] = React.useState<PairResponse | null>(null);
  const [healthByKey, setHealthByKey] = React.useState<Record<string, string>>({});
  const [busyKey, setBusyKey] = React.useState<string | null>(null);
  const [manifestText, setManifestText] = React.useState(STARTER_MANIFEST);
  const [manifestReport, setManifestReport] = React.useState<Record<string, unknown> | null>(null);
  const [approvedToken, setApprovedToken] = React.useState<PairResponse | null>(null);

  const projects = data || [];

  async function createPairing() {
    setActionError(null);
    setMessage(null);
    setPairResult(null);
    const key = pairProjectKey.trim();
    if (!key) {
      setActionError("Enter a project key for pairing.");
      return;
    }
    const scopes = pairScopes
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const response = await ceApi("/sidecar/v1/pair/codes", {
        method: "POST",
        body: JSON.stringify({ project_key: key, requested_scopes: scopes }),
      });
      const body = (await response.json().catch(() => ({}))) as PairResponse & {
        detail?: string;
        error?: string;
      };
      if (!response.ok) {
        setActionError(
          typeof body.detail === "string"
            ? body.detail
            : body.error || `Pairing failed (${response.status})`,
        );
        return;
      }
      setPairResult(body);
      setMessage("Pairing code created. Share it once with the product; it expires.");
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Pairing failed");
    }
  }

  function parseManifest(): Record<string, unknown> | null {
    try {
      return JSON.parse(manifestText) as Record<string, unknown>;
    } catch (err) {
      setActionError(err instanceof Error ? `Invalid JSON: ${err.message}` : "Invalid manifest JSON");
      return null;
    }
  }

  async function validateOrApplyManifest(apply: boolean) {
    setActionError(null);
    setMessage(null);
    const manifest = parseManifest();
    if (!manifest) return;
    const path = apply ? "/sidecar/v1/admin/apply" : "/sidecar/v1/admin/manifests/validate";
    const response = await ceApi(path, {
      method: "POST",
      body: JSON.stringify({ manifest, confirm_risky: false }),
    });
    const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    setManifestReport(body);
    if (!response.ok) {
      setActionError(parseApiErrorMessage(body, `${apply ? "Apply" : "Validation"} failed`));
      return;
    }
    if (apply) {
      setMessage(`Project ${String(body.project_key || "")} saved and applied.`);
      await mutate();
    } else {
      setMessage(body.ok ? "Manifest is valid." : "Manifest has validation issues.");
    }
  }

  async function editProject(key: string) {
    const response = await ceApi(`/sidecar/v1/admin/projects/${encodeURIComponent(key)}/manifest`);
    const body = (await response.json().catch(() => ({}))) as { manifest?: Record<string, unknown> };
    if (!response.ok || !body.manifest) {
      setActionError(parseApiErrorMessage(body, `Could not load ${key}`));
      return;
    }
    setManifestText(JSON.stringify(body.manifest, null, 2));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function deleteProject(key: string) {
    if (!window.confirm(`Delete sidecar project ${key}? This does not delete the external application.`)) return;
    const response = await ceApi(`/sidecar/v1/admin/projects/${encodeURIComponent(key)}`, { method: "DELETE" });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      setActionError(parseApiErrorMessage(body, `Could not delete ${key}`));
      return;
    }
    setMessage(`Deleted sidecar project ${key}.`);
    await mutate();
  }

  async function checkConnectivity(key: string) {
    setBusyKey(key);
    const response = await ceApi(
      `/sidecar/v1/admin/projects/${encodeURIComponent(key)}/connectivity-check`,
      { method: "POST" },
    );
    const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    setBusyKey(null);
    if (!response.ok) {
      setActionError(parseApiErrorMessage(body, `Connectivity check failed for ${key}`));
      return;
    }
    setHealthByKey((previous) => ({ ...previous, [key]: String(body.status || "unknown") }));
    setMessage(
      `${key}: ${String(body.status || "unknown")}${body.http_status ? ` (HTTP ${body.http_status})` : ""}`,
    );
  }

  async function approvePairing() {
    const code = pairResult?.pairing_code || pairResult?.pairingCode;
    if (!code) return;
    const response = await ceApi("/sidecar/v1/pair/approve", {
      method: "POST",
      body: JSON.stringify({ pairing_code: code }),
    });
    const body = (await response.json().catch(() => ({}))) as PairResponse;
    if (!response.ok) {
      setActionError(parseApiErrorMessage(body, "Pairing approval failed"));
      return;
    }
    setApprovedToken(body);
    setMessage("Pairing approved. Copy the token now; Keprix will not display it again.");
  }

  async function revokeApprovedToken() {
    if (!approvedToken?.jti) return;
    const response = await ceApi("/sidecar/v1/tokens/revoke", {
      method: "POST",
      body: JSON.stringify({ jti: approvedToken.jti }),
    });
    if (!response.ok) {
      setActionError("Token revocation failed.");
      return;
    }
    setApprovedToken(null);
    setMessage("Workload token revoked.");
  }

  async function refreshHealth(key: string) {
    setBusyKey(key);
    setActionError(null);
    try {
      const response = await ceApi(`/sidecar/v1/projects/${encodeURIComponent(key)}/health`);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setHealthByKey((prev) => ({ ...prev, [key]: `error:${response.status}` }));
        setActionError(
          typeof body.detail === "string"
            ? body.detail
            : `Health check failed for ${key}`,
        );
        return;
      }
      const status =
        (typeof body.status === "string" && body.status) ||
        (typeof body.health === "string" && body.health) ||
        "ok";
      setHealthByKey((prev) => ({ ...prev, [key]: status }));
      setMessage(`Health for ${key}: ${status}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Health check failed");
    } finally {
      setBusyKey(null);
    }
  }

  async function setKillSwitch(key: string, engaged: boolean) {
    setBusyKey(key);
    setActionError(null);
    try {
      const response = await ceApi(
        `/sidecar/v1/projects/${encodeURIComponent(key)}/kill-switch`,
        {
          method: "POST",
          body: JSON.stringify({ engaged }),
        },
      );
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setActionError(
          typeof body.detail === "string"
            ? body.detail
            : `Kill switch update failed (${response.status})`,
        );
        return;
      }
      setMessage(engaged ? `Kill switch engaged for ${key}` : `Kill switch cleared for ${key}`);
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Kill switch update failed");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <Box>
      <PageHeader
        title="Sidecars"
        description="Pair product projects with the Keprix Universal Sidecar, check health, and manage kill switches. Propreneur pack CRUD readiness is a separate surface."
      />

      <Alert severity="info" sx={{ mb: 2 }}>
        Universal Sidecar project health is connectivity only. For Propreneur live or Soft Wall
        CRUD readiness, open{" "}
        <Button component="a" href="/settings/sidecars/propreneur" size="small" sx={{ textTransform: "none" }}>
          Propreneur pack readiness
        </Button>
        .
      </Alert>

      {error ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Could not load projects from `/sidecar/v1/projects`. The API may be
          unavailable or you may lack operator access. {String(error.message || error)}
        </Alert>
      ) : null}
      {actionError ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Project manifest</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Create or update a persistent sidecar project. Secret values are rejected; use an env, vault, or secret reference.
          </Typography>
          <TextField
            label="keprix.sidecar.json"
            value={manifestText}
            onChange={(event) => setManifestText(event.target.value)}
            multiline
            minRows={14}
            fullWidth
            sx={{ fontFamily: "monospace" }}
          />
          <Stack direction="row" spacing={1} sx={{ mt: 2 }} flexWrap="wrap" useFlexGap>
            <Button variant="outlined" onClick={() => validateOrApplyManifest(false)}>Validate and preview</Button>
            <Button variant="contained" onClick={() => validateOrApplyManifest(true)}>Save and apply</Button>
            <Button variant="text" onClick={() => { setManifestText(STARTER_MANIFEST); setManifestReport(null); }}>New manifest</Button>
          </Stack>
          {manifestReport ? (
            <Box component="pre" sx={{ mt: 2, p: 2, bgcolor: "action.hover", overflow: "auto", fontSize: 12 }}>
              {JSON.stringify(manifestReport, null, 2)}
            </Box>
          ) : null}
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Pairing
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Create a one-time pairing code for a project. Codes are not demo
            fixtures; they come from the live sidecar when available.
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }}>
            <TextField
              label="Project key"
              size="small"
              value={pairProjectKey}
              onChange={(e) => setPairProjectKey(e.target.value)}
              placeholder="demo"
              fullWidth
            />
            <TextField
              label="Requested scopes"
              size="small"
              value={pairScopes}
              onChange={(e) => setPairScopes(e.target.value)}
              placeholder="discover,invoke:summarise"
              fullWidth
            />
            <Button variant="contained" onClick={createPairing} sx={{ whiteSpace: "nowrap" }}>
              Create code
            </Button>
          </Stack>
          {pairResult ? (
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2">
                Code: <strong>{pairResult.pairing_code || pairResult.pairingCode || "(see response)"}</strong>
              </Typography>
              {(pairResult.expires_at || pairResult.expiresAt) ? (
                <Typography variant="body2" color="text.secondary">
                  Expires: {pairResult.expires_at || pairResult.expiresAt}
                </Typography>
              ) : null}
              <Button size="small" variant="contained" sx={{ mt: 1 }} onClick={approvePairing}>
                Approve and issue token
              </Button>
            </Box>
          ) : null}
          {approvedToken?.access_token ? (
            <Alert severity="warning" sx={{ mt: 2 }}>
              <Typography variant="body2">Copy this token now. It is shown once.</Typography>
              <Box component="code" sx={{ display: "block", overflowWrap: "anywhere", my: 1 }}>
                {approvedToken.access_token}
              </Box>
              <Button size="small" color="error" onClick={revokeApprovedToken}>Revoke token</Button>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Typography variant="h6" gutterBottom>
        Projects
      </Typography>
      {isLoading ? (
        <Typography color="text.secondary">Loading projects...</Typography>
      ) : null}
      {!isLoading && projects.length === 0 ? (
        <Typography color="text.secondary">
          No registered sidecar projects yet. Register a `keprix.sidecar.yaml`
          and pair a product to see entries here.
        </Typography>
      ) : null}

      <Stack spacing={2} sx={{ mt: 1 }}>
        {projects.map((project) => {
          const key = projectKeyOf(project);
          if (!key) return null;
          const kill = Boolean(project.kill_switch ?? project.killSwitch);
          const health = healthByKey[key] || healthLabel(project);
          const busy = busyKey === key;
          return (
            <Card key={key} variant="outlined">
              <CardContent>
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={2}
                  alignItems={{ md: "center" }}
                  justifyContent="space-between"
                >
                  <Box>
                    <Typography variant="subtitle1">
                      {project.display_name || project.displayName || key}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {key}
                      {project.environment ? ` · ${project.environment}` : ""}
                    </Typography>
                    <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                      <Chip size="small" label={`health: ${health}`} />
                      <Chip
                        size="small"
                        color={kill ? "error" : "default"}
                        label={kill ? "kill switch on" : "kill switch off"}
                      />
                    </Stack>
                  </Box>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={busy}
                      onClick={() => refreshHealth(key)}
                    >
                      Refresh health
                    </Button>
                    <Button size="small" variant="outlined" disabled={busy} onClick={() => checkConnectivity(key)}>
                      Test connection
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => editProject(key)}>Edit manifest</Button>
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      disabled={busy || kill}
                      onClick={() => setKillSwitch(key, true)}
                    >
                      Engage kill switch
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={busy || !kill}
                      onClick={() => setKillSwitch(key, false)}
                    >
                      Clear kill switch
                    </Button>
                    <Button size="small" color="error" onClick={() => deleteProject(key)}>Delete</Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
    </Box>
  );
}

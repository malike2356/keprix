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
import { ceApi } from "@/lib/ce-api";

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
};

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
        description="Pair product projects with the Keprix Universal Sidecar, check health, and manage kill switches."
      />

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
            </Box>
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

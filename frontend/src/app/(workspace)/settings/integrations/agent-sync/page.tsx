"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import SaveIcon from "@mui/icons-material/Save";
import SearchIcon from "@mui/icons-material/Search";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Status = {
  enabled: boolean;
  configured: boolean;
  has_token?: boolean;
  hasToken?: boolean;
  repo: string | null;
  branch: string;
  product: string;
  pull_interval_minutes?: number;
  pullIntervalMinutes?: number;
  push_interval_minutes?: number;
  pushIntervalMinutes?: number;
  allowed_folders?: string[];
  allowedFolders?: string[];
  human_edits_win?: boolean;
  humanEditsWin?: boolean;
  last_pull_at?: string | null;
  lastPullAt?: string | null;
  last_push_at?: string | null;
  lastPushAt?: string | null;
  last_error?: string | null;
  lastError?: string | null;
  indexed_chunks?: number;
  indexedChunks?: number;
  clone_exists?: boolean;
  cloneExists?: boolean;
  local_path?: string;
  localPath?: string;
};

type SearchHit = { path: string; score: number; snippet: string };

const fetcher = async (url: string): Promise<Status> => {
  const response = await ceApi(url);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

export default function AgentSyncSettingsPage() {
  const { data, error, mutate, isLoading } = useSWR("/api/agent-sync/status", fetcher);
  const [message, setMessage] = React.useState<string | null>(null);
  const [enabled, setEnabled] = React.useState(false);
  const [owner, setOwner] = React.useState("malike2356");
  const [repo, setRepo] = React.useState("agent-sync");
  const [branch, setBranch] = React.useState("main");
  const [product, setProduct] = React.useState("keprix");
  const [pullMinutes, setPullMinutes] = React.useState(15);
  const [pushMinutes, setPushMinutes] = React.useState(0);
  const [folders, setFolders] = React.useState("memory, skills, plans, AGENTS.md");
  const [humanEditsWin, setHumanEditsWin] = React.useState(true);
  const [token, setToken] = React.useState("");
  const [clearToken, setClearToken] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");
  const [hits, setHits] = React.useState<SearchHit[]>([]);

  React.useEffect(() => {
    if (!data) return;
    setEnabled(Boolean(data.enabled));
    const [o, r] = (data.repo || "malike2356/agent-sync").split("/");
    setOwner(o || "malike2356");
    setRepo(r || "agent-sync");
    setBranch(data.branch || "main");
    setProduct(data.product || "keprix");
    setPullMinutes(data.pull_interval_minutes ?? data.pullIntervalMinutes ?? 15);
    setPushMinutes(data.push_interval_minutes ?? data.pushIntervalMinutes ?? 0);
    const allowed = data.allowed_folders ?? data.allowedFolders ?? ["memory", "skills", "plans", "AGENTS.md"];
    setFolders(allowed.join(", "));
    setHumanEditsWin(data.human_edits_win ?? data.humanEditsWin ?? true);
  }, [data]);

  async function save() {
    const allowedFolders = folders
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const payload: Record<string, unknown> = {
      enabled,
      owner,
      repo,
      branch,
      product,
      pullIntervalMinutes: pullMinutes,
      pushIntervalMinutes: pushMinutes,
      allowedFolders,
      humanEditsWin,
    };
    if (clearToken) payload.token = null;
    else if (token.trim()) payload.token = token.trim();

    const response = await ceApi("/api/agent-sync/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      setMessage(typeof body.detail === "string" ? body.detail : body.error || "Save failed");
      return;
    }
    setToken("");
    setClearToken(false);
    setMessage("Saved in Settings. Scheduler refreshed.");
    void mutate();
  }

  async function run(action: "pull" | "push" | "index") {
    const response = await ceApi(`/api/agent-sync/${action}`, {
      method: "POST",
      body: action === "push" ? JSON.stringify({}) : undefined,
    });
    const payload = await response.json();
    if (action === "index") {
      setMessage(payload.ok ? `Indexed ${payload.indexed ?? 0} chunks` : payload.error || "Index failed");
    } else {
      setMessage(payload.ok ? `${action} ok` : payload.error || `${action} failed`);
    }
    void mutate();
  }

  async function search() {
    const response = await ceApi("/api/agent-sync/search", {
      method: "POST",
      body: JSON.stringify({ query: searchQuery, limit: 8 }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setMessage(payload.detail || payload.error || "Search failed");
      return;
    }
    setHits(payload.hits || []);
    setMessage(`Found ${(payload.hits || []).length} hits`);
  }

  const hasToken = Boolean(data?.has_token ?? data?.hasToken);
  const indexed = data?.indexed_chunks ?? data?.indexedChunks ?? 0;
  const lastError = data?.last_error ?? data?.lastError;
  const lastPull = data?.last_pull_at ?? data?.lastPullAt;
  const lastPush = data?.last_push_at ?? data?.lastPushAt;
  const localPath = data?.local_path ?? data?.localPath;

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="GitHub agent-sync"
        description="Configure durable shared memory with Fowler (Hermes), Carina, and Aiva from this page. Obsidian vault sync is Settings -> Syncthing, not this page."
      />
      {message ? (
        <Alert severity={/fail|Missing|error/i.test(message) ? "warning" : "info"} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {error ? <Alert severity="error">Failed to load agent-sync status. Sign in and retry.</Alert> : null}
      {lastError ? <Alert severity="warning">Last sync error: {lastError}</Alert> : null}

      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Chip color={data?.enabled ? "success" : "default"} label={data?.enabled ? "Enabled" : "Disabled"} />
          <Chip variant="outlined" label={hasToken ? "Token saved" : "Token needed"} color={hasToken ? "success" : "warning"} />
          <Chip variant="outlined" label={`${indexed} indexed`} />
          {data?.clone_exists || data?.cloneExists ? <Chip variant="outlined" label="Clone ready" color="success" /> : null}
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Paste a fine-grained GitHub PAT below, turn on sync, Save, then Pull. Use product <strong>keprix</strong> here and{" "}
          <strong>hermes</strong> on Fowler. Defaults to <code>malike2356/agent-sync</code>.
          {lastPull ? ` Last pull: ${lastPull}.` : ""}
          {lastPush ? ` Last push: ${lastPush}.` : ""}
        </Typography>
        {localPath ? (
          <Typography variant="caption" color="text.secondary">
            Local clone: {localPath}
          </Typography>
        ) : null}

        <FormControlLabel
          control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
          label="Enable GitHub agent-sync"
        />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <TextField label="GitHub owner" value={owner} onChange={(e) => setOwner(e.target.value)} fullWidth />
          <TextField label="Repo" value={repo} onChange={(e) => setRepo(e.target.value)} fullWidth />
          <TextField label="Branch" value={branch} onChange={(e) => setBranch(e.target.value)} fullWidth />
        </Stack>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <TextField select label="Product mount" value={product} onChange={(e) => setProduct(e.target.value)} fullWidth>
            {[
              { value: "keprix", label: "keprix (this install)" },
              { value: "hermes", label: "hermes (Fowler)" },
              { value: "carina", label: "carina" },
              { value: "aiva", label: "aiva" },
              { value: "shared", label: "shared" },
            ].map((item) => (
              <MenuItem key={item.value} value={item.value}>
                {item.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Pull every (minutes)"
            type="number"
            value={pullMinutes}
            onChange={(e) => setPullMinutes(Number(e.target.value) || 15)}
            fullWidth
          />
          <TextField
            label="Push every (0 = Save/note only)"
            type="number"
            value={pushMinutes}
            onChange={(e) => setPushMinutes(Number(e.target.value) || 0)}
            fullWidth
          />
        </Stack>
        <TextField
          label="Allowed folders (comma-separated)"
          value={folders}
          onChange={(e) => setFolders(e.target.value)}
          fullWidth
          helperText="Folders this install mounts from the shared repo."
        />
        <FormControlLabel
          control={<Switch checked={humanEditsWin} onChange={(e) => setHumanEditsWin(e.target.checked)} />}
          label="Keep local human edits on pull"
        />
        <TextField
          label="GitHub token (PAT)"
          type="password"
          value={token}
          onChange={(e) => {
            setToken(e.target.value);
            setClearToken(false);
          }}
          placeholder={hasToken ? "Leave blank to keep saved token" : "Paste ghp_... or github_pat_..."}
          fullWidth
          helperText="Saved in the Keprix data dir via this GUI (mode 600). Not committed."
        />
        <FormControlLabel
          control={<Switch checked={clearToken} onChange={(e) => setClearToken(e.target.checked)} disabled={!hasToken} />}
          label="Clear saved token on Save"
        />
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button variant="contained" startIcon={<SaveIcon />} onClick={() => void save()} disabled={isLoading}>
            Save
          </Button>
          <Button variant="outlined" startIcon={<CloudDownloadIcon />} onClick={() => void run("pull")} disabled={!enabled}>
            Pull now
          </Button>
          <Button variant="outlined" startIcon={<CloudUploadIcon />} onClick={() => void run("push")} disabled={!enabled}>
            Push now
          </Button>
          <Button variant="outlined" onClick={() => void run("index")} disabled={!enabled}>
            Rebuild index
          </Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Typography variant="h6">Search shared memory</Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField
            label="Query"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            fullWidth
            onKeyDown={(e) => {
              if (e.key === "Enter") void search();
            }}
          />
          <Button variant="outlined" startIcon={<SearchIcon />} onClick={() => void search()} disabled={!searchQuery.trim()}>
            Search
          </Button>
        </Stack>
        {hits.map((hit) => (
          <Box key={`${hit.path}-${hit.score}`} sx={{ borderTop: 1, borderColor: "divider", pt: 1 }}>
            <Typography variant="subtitle2">{hit.path}</Typography>
            <Typography variant="body2" color="text.secondary">
              {hit.snippet}
            </Typography>
          </Box>
        ))}
        {!hits.length ? (
          <Typography variant="body2" color="text.secondary">
            Pull once, then search durable notes from Fowler / Carina / Keprix.
          </Typography>
        ) : null}
      </Paper>
    </Box>
  );
}

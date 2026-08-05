"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { IconPlayerPlay } from "@tabler/icons-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ceApi } from "@/lib/ce-api";
import DashboardCard from "@/components/cards/DashboardCard";
import { GitCommitPanel } from "@/components/coding/GitCommitPanel";
import PreflightBanner, { type PreflightReport } from "@/components/coding/PreflightBanner";
import { RepoMapPanel } from "@/components/coding/RepoMapPanel";
import { TestRunPanel } from "@/components/coding/TestRunPanel";

type RepoMapResponse = {
  compact: string;
  files: string[];
  tests: string[];
  routes: string[];
  recently_changed: string[];
  ignored_count: number;
};

type ChatResponse = {
  ok: boolean;
  diff: string;
  test_summary: string;
  commit: {
    message: string;
    needs_approval: boolean;
    commit_hash: string | null;
    error: string | null;
  };
  export_markdown: string;
  error: string | null;
};

export default function AdminCodingPage() {
  const [repoPath, setRepoPath] = useState("");
  const [message, setMessage] = useState("Add marker to README.md");
  const [repoMap, setRepoMap] = useState<RepoMapResponse | null>(null);
  const [chat, setChat] = useState<ChatResponse | null>(null);
  const [commands, setCommands] = useState<{ test_command: string | null; lint_command: string | null } | null>(
    null,
  );
  const [preflight, setPreflight] = useState<PreflightReport | null>(null);
  const [preflightEnabled, setPreflightEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const parseJson = async <T,>(response: Response, fallback: string): Promise<T> => {
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(
        (payload as { detail?: string; error?: string }).detail ||
          (payload as { error?: string }).error ||
          fallback,
      );
    }
    return response.json();
  };

  const loadRepoMap = async (path: string) => {
    const payload = await parseJson<RepoMapResponse>(
      await ceApi(`/api/coding/repo-map?repo_path=${encodeURIComponent(path)}`),
      "Failed to load repo map",
    );
    setRepoMap(payload);
    const detected = await parseJson<{ test_command: string | null; lint_command: string | null }>(
      await ceApi(`/api/coding/lint-test/detect?repo_path=${encodeURIComponent(path)}`),
      "Failed to detect commands",
    );
    setCommands(detected);
  };

  useEffect(() => {
    if (!repoPath) return;
    loadRepoMap(repoPath).catch((err: Error) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoPath]);

  const runChat = async () => {
    if (!repoPath) return;
    setLoading(true);
    setError(null);
    try {
      if (preflightEnabled) {
        const preflightPayload = await parseJson<{ report: PreflightReport }>(
          await ceApi("/api/coding/preflight/run", {
            method: "POST",
            body: JSON.stringify({
              session_id: `coding:${repoPath}`,
              intent: message,
              repo_path: repoPath,
              repo_index_present: Boolean(repoMap),
              changed_files: repoMap?.recently_changed || [],
            }),
          }),
          "Preflight failed",
        );
        setPreflight(preflightPayload.report);
        if (preflightPayload.report.overall === "block" && !preflightPayload.report.override_applied) {
          setLoading(false);
          return;
        }
      }
      const payload = await parseJson<ChatResponse>(
        await ceApi("/api/coding/chat", {
          method: "POST",
          body: JSON.stringify({
            message,
            repo_path: repoPath,
            commit_approved: false,
          }),
        }),
        "Chat run failed",
      );
      setChat(payload);
      await loadRepoMap(repoPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat run failed");
    } finally {
      setLoading(false);
    }
  };

  const approveCommit = async () => {
    if (!repoPath || !chat?.commit.message) return;
    await ceApi("/api/coding/git/commit", {
      method: "POST",
      body: JSON.stringify({
        repo_path: repoPath,
        message: chat.commit.message,
        approved: true,
      }),
    });
    await runChat();
  };

  const overridePreflight = async () => {
    if (!repoPath) return;
    const payload = await parseJson<{ report: PreflightReport }>(
      await ceApi(`/api/coding/preflight/${encodeURIComponent(`coding:${repoPath}`)}/override`, {
        method: "POST",
      }),
      "Preflight override failed",
    );
    setPreflight(payload.report);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: "-0.02em" }}>
          Coding workspace
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Git-native coding with repo maps, lint/test loops, and commit proposals. Point at a local repo, describe the
          task, then review the diff before approving a commit.
        </Typography>
      </Box>

      <DashboardCard title="Run a coding task" subtitle="Step 1: repo path. Step 2: task. Step 3: review output below.">
        <Stack spacing={2.5}>
          <TextField
            label="Repository path"
            placeholder="/path/to/your/project"
            value={repoPath}
            onChange={(event) => setRepoPath(event.target.value)}
            fullWidth
            helperText="Absolute path to a git repository on this machine. Secrets and ignored paths are excluded from the repo map."
          />
          <TextField
            label="Coding task"
            placeholder="Describe the change you want Keprix to make"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            fullWidth
            multiline
            minRows={3}
          />
          <Box>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Button
                variant="contained"
                startIcon={<IconPlayerPlay size={18} stroke={1.75} />}
                onClick={() => void runChat()}
                disabled={!repoPath.trim() || !message.trim() || loading}
              >
                {loading ? "Running..." : "Run coding session"}
              </Button>
              <Button
                variant={preflightEnabled ? "contained" : "outlined"}
                color="secondary"
                onClick={() => setPreflightEnabled((value) => !value)}
              >
                Preflight
              </Button>
              <Button
                variant="outlined"
                component={Link}
                href={repoPath.trim() ? `/design/preview?path=${encodeURIComponent(repoPath.trim())}` : "/design/preview"}
              >
                Design preview
              </Button>
            </Stack>
          </Box>
        </Stack>
      </DashboardCard>

      {error ? <Alert severity="error">{error}</Alert> : null}
      <PreflightBanner report={preflight} onOverride={() => void overridePreflight()} />

      {!repoPath.trim() ? (
        <Alert severity="info">Enter a repository path to load the repo map and run coding tasks.</Alert>
      ) : null}

      <Grid container spacing={2} alignItems="stretch">
        <Grid size={{ xs: 12, lg: 7 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <RepoMapPanel
              repoPath={repoPath}
              compact={repoMap?.compact}
              files={repoMap?.files}
              tests={repoMap?.tests}
              routes={repoMap?.routes}
              recentlyChanged={repoMap?.recently_changed}
              ignoredCount={repoMap?.ignored_count}
              loading={!repoMap && !!repoPath}
              error={null}
            />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <TestRunPanel
              testCommand={commands?.test_command}
              lintCommand={commands?.lint_command}
              testSummary={chat?.test_summary}
              ok={chat?.ok}
              loading={loading}
              onRun={runChat}
            />
          </Box>
        </Grid>
      </Grid>

      <GitCommitPanel
        diff={chat?.diff || ""}
        proposedMessage={chat?.commit.message || ""}
        stagedFiles={repoMap?.recently_changed || []}
        needsApproval={chat?.commit.needs_approval ?? true}
        commitHash={chat?.commit.commit_hash}
        error={chat?.commit.error}
        onCommit={approveCommit}
      />

      {chat?.export_markdown ? (
        <DashboardCard title="Web chat export" subtitle="Copy this bundle into web chat if you need a fallback handoff.">
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 2,
              maxHeight: 280,
              overflow: "auto",
              borderRadius: 1,
              bgcolor: "action.hover",
              fontSize: "0.75rem",
              fontFamily: "monospace",
            }}
          >
            {chat.export_markdown}
          </Box>
        </DashboardCard>
      ) : null}
    </Box>
  );
}

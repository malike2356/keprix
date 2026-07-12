"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { ceApi } from "@/lib/ce-api";

type PlaybookPayload = {
  ok: boolean;
  technique_count: number;
  techniques: Array<{ id: string; title: string; summary: string; default_on: boolean }>;
};

type GuardrailsPayload = {
  ok: boolean;
  enabled: boolean;
  workspace_root: string;
  approvals_required: boolean;
  vault_auto_backup: boolean;
};

type ErrorPasteResult = {
  status: string;
  classification?: string;
  output?: string;
  error?: string;
};

async function fetchPlaybook(): Promise<PlaybookPayload> {
  const response = await ceApi("/api/agent-os/token-playbook");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as PlaybookPayload;
}

async function fetchGuardrails(): Promise<GuardrailsPayload> {
  const response = await ceApi("/api/agent-os/guardrails");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as GuardrailsPayload;
}

export default function ShipDefaultsPanel() {
  const { data: playbook, error: playbookError } = useSWR("agent-os-token-playbook", fetchPlaybook);
  const { data: guardrails, error: guardrailsError, mutate: mutateGuardrails } = useSWR(
    "agent-os-guardrails",
    fetchGuardrails,
  );
  const [expanded, setExpanded] = React.useState(false);
  const [backupMsg, setBackupMsg] = React.useState<string | null>(null);
  const [backupBusy, setBackupBusy] = React.useState(false);
  const [errorText, setErrorText] = React.useState("");
  const [pasteResult, setPasteResult] = React.useState<ErrorPasteResult | null>(null);
  const [pasteBusy, setPasteBusy] = React.useState(false);

  const backupVault = async () => {
    setBackupBusy(true);
    setBackupMsg(null);
    try {
      const response = await ceApi("/api/agent-os/guardrails/backup-vault", { method: "POST" });
      const body = (await response.json()) as { ok?: boolean; path?: string; error?: string; reason?: string };
      if (!response.ok || body.ok === false) {
        setBackupMsg(body.error || body.reason || "Backup failed");
        return;
      }
      setBackupMsg(body.path ? `Saved ${body.path}` : "Vault backup complete");
      await mutateGuardrails();
    } catch (err) {
      setBackupMsg(err instanceof Error ? err.message : "Backup failed");
    } finally {
      setBackupBusy(false);
    }
  };

  const runErrorPaste = async () => {
    setPasteBusy(true);
    setPasteResult(null);
    try {
      const response = await ceApi("/api/agent-os/error-paste", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ error_text: errorText }),
      });
      const body = (await response.json()) as ErrorPasteResult;
      if (!response.ok) {
        setPasteResult({ status: "error", error: JSON.stringify(body) });
        return;
      }
      setPasteResult(body);
    } catch (err) {
      setPasteResult({ status: "error", error: err instanceof Error ? err.message : "Request failed" });
    } finally {
      setPasteBusy(false);
    }
  };

  return (
    <Paper
      variant="outlined"
      className="agent-os-glass-panel"
      sx={{
        p: 2,
        mt: 2,
        bgcolor: "action.hover",
        backdropFilter: "blur(8px)",
        backgroundImage: "linear-gradient(180deg, rgba(255,255,255,0.04), transparent)",
      }}
    >
      <Typography variant="h6" sx={{ mb: 1 }}>
        Ship defaults
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Token playbook, guardrails, and the error paste loop; Phase 5 surfaces on glass.
      </Typography>

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" } }}>
        <Stack spacing={1}>
          <Typography variant="subtitle2">Token playbook</Typography>
          {playbookError ? <Alert severity="error">{playbookError.message}</Alert> : null}
          {playbook ? (
            <>
              <Chip size="small" label={`${playbook.technique_count} techniques`} />
              {(expanded ? playbook.techniques : playbook.techniques.slice(0, 4)).map((item) => (
                <Box key={item.id}>
                  <Typography variant="body2" fontWeight={600}>
                    {item.title}
                    {!item.default_on ? (
                      <Typography component="span" variant="caption" color="text.secondary">
                        {" "}
                        (opt-in)
                      </Typography>
                    ) : null}
                  </Typography>
                  {expanded ? (
                    <Typography variant="caption" color="text.secondary">
                      {item.summary}
                    </Typography>
                  ) : null}
                </Box>
              ))}
              <Button size="small" onClick={() => setExpanded((v) => !v)}>
                {expanded ? "Show less" : "Show all"}
              </Button>
            </>
          ) : (
            <LinearProgress />
          )}
        </Stack>

        <Stack spacing={1}>
          <Typography variant="subtitle2">Guardrails</Typography>
          {guardrailsError ? <Alert severity="error">{guardrailsError.message}</Alert> : null}
          {guardrails ? (
            <>
              <Chip size="small" color={guardrails.enabled ? "success" : "default"} label={guardrails.enabled ? "On" : "Off"} />
              <Typography variant="caption" color="text.secondary" sx={{ wordBreak: "break-all" }}>
                Workspace: {guardrails.workspace_root}
              </Typography>
              <Typography variant="body2">
                Approvals: {guardrails.approvals_required ? "required" : "relaxed"}
              </Typography>
              <Typography variant="body2">
                Vault auto-backup: {guardrails.vault_auto_backup ? "on" : "off"}
              </Typography>
              <Button size="small" variant="outlined" disabled={backupBusy} onClick={() => void backupVault()}>
                {backupBusy ? "Backing up…" : "Backup vault"}
              </Button>
              {backupMsg ? (
                <Typography variant="caption" color="text.secondary">
                  {backupMsg}
                </Typography>
              ) : null}
            </>
          ) : (
            <LinearProgress />
          )}
        </Stack>

        <Stack spacing={1}>
          <Typography variant="subtitle2">Error paste loop</Typography>
          <TextField
            multiline
            minRows={4}
            size="small"
            placeholder="Paste a traceback…"
            value={errorText}
            onChange={(event) => setErrorText(event.target.value)}
          />
          <Button
            size="small"
            variant="contained"
            disabled={pasteBusy || !errorText.trim()}
            onClick={() => void runErrorPaste()}
          >
            {pasteBusy ? "Classifying…" : "Classify error"}
          </Button>
          <Collapse in={Boolean(pasteResult)}>
            {pasteResult ? (
              <Box>
                {pasteResult.classification ? (
                  <Chip size="small" label={pasteResult.classification} sx={{ mb: 1 }} />
                ) : null}
                {pasteResult.error ? <Alert severity="error">{pasteResult.error}</Alert> : null}
                {pasteResult.output ? (
                  <Typography
                    component="pre"
                    variant="caption"
                    sx={{ whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto" }}
                  >
                    {pasteResult.output}
                  </Typography>
                ) : null}
              </Box>
            ) : null}
          </Collapse>
        </Stack>
      </Box>
    </Paper>
  );
}

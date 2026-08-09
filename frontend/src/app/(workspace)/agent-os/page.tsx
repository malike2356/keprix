"use client";

import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import ActionBoardMetrics from "@/components/agent-os/ActionBoardMetrics";
import ActionPinButton, { type ActionPin } from "@/components/agent-os/ActionPinButton";
import ActionResultPanel, { type HeadlessRun } from "@/components/agent-os/ActionResultPanel";
import ActionScheduleDialog from "@/components/agent-os/ActionScheduleDialog";
import AgentOsMoreLinks from "@/components/agent-os/AgentOsMoreLinks";
import { AGENT_OS_HUB_HOME } from "@/components/agent-os/AgentOsSubnav";
import ErrorState from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";
import Stack from "@mui/material/Stack";

type BoardAction = {
  type: "skill" | "playbook" | "agent_app" | "cron";
  id: string;
  label: string;
  edit_url?: string;
};

type BoardPayload = {
  config: { pins: ActionPin[] };
  actions: BoardAction[];
  metrics: {
    token_burn_24h: number;
    runs_today: number;
    failed_runs: number;
    pending_approvals: number;
  };
};

async function fetchBoard(): Promise<BoardPayload> {
  const response = await ceApi("/api/agent-os/board");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as BoardPayload;
}

export default function AgentOsActionBoardPage() {
  const search = useSearchParams();
  const { data, mutate, error } = useSWR("agent-os-board", fetchBoard);
  const [query, setQuery] = React.useState("");
  const [typeFilter, setTypeFilter] = React.useState("all");
  const [runningId, setRunningId] = React.useState<string | null>(null);
  const [lastRun, setLastRun] = React.useState<HeadlessRun | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [scheduleSkill, setScheduleSkill] = React.useState<string | null>(null);

  const pins = data?.config.pins ?? [];
  const actions = (data?.actions ?? []).filter((action) => {
    if (typeFilter !== "all" && action.type !== typeFilter) return false;
    const needle = `${action.label} ${action.id}`.toLowerCase();
    return needle.includes(query.toLowerCase());
  });

  const runAction = React.useCallback(async (pin: ActionPin) => {
    setRunningId(pin.pin_id);
    setMessage(null);
    const path =
      pin.type === "agent_app"
        ? `/api/agent-os/run/agent-app/${encodeURIComponent(pin.id)}`
        : `/api/agent-os/run/${pin.type}/${encodeURIComponent(pin.id)}`;
    try {
      const response = await ceApi(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ params: {}, inputs: {} }),
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as HeadlessRun;
      setLastRun(payload);
      await mutate();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunningId(null);
    }
  }, [mutate]);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.tagName === "INPUT" || target?.tagName === "TEXTAREA") return;
      for (const pin of pins) {
        if (!pin.shortcut) continue;
        const parts = pin.shortcut.toLowerCase().split("+");
        const key = parts[parts.length - 1];
        const matches =
          event.key.toLowerCase() === key.toLowerCase() &&
          event.ctrlKey === parts.includes("ctrl") &&
          event.shiftKey === parts.includes("shift") &&
          event.altKey === parts.includes("alt") &&
          event.metaKey === parts.includes("meta");
        if (matches) {
          event.preventDefault();
          void runAction(pin);
          break;
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [pins, runAction]);

  React.useEffect(() => {
    const runPinId = search.get("run");
    if (!runPinId || pins.length === 0) return;
    const pin = pins.find((item) => item.pin_id === runPinId || item.id === runPinId);
    if (pin) void runAction(pin);
  }, [pins, runAction, search]);

  const addPin = async (action: BoardAction) => {
    const response = await ceApi("/api/agent-os/board/pins", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: action.type, id: action.id, label: action.label }),
    });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    await mutate();
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Action board"
        description="Run pinned skills, playbooks, and Agent Apps without opening a chat tab."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: AGENT_OS_HUB_HOME },
          { label: "Board" },
        ]}
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button component="a" href="/agent-os/glass" variant="outlined" size="small">
              Glass
            </Button>
            <Button component="a" href="/agent-os/onboarding" variant="outlined" size="small">
              Onboarding
            </Button>
            <Button component="a" href="/usage" variant="outlined" size="small">
              Usage
            </Button>
            <Button component="a" href="/agent-os/runs" variant="outlined" size="small">
              Run ledger
            </Button>
          </Stack>
        }
      />
      {data?.metrics ? <ActionBoardMetrics metrics={data.metrics} /> : null}
      {error ? (
        <ErrorState
          title="Board failed to load"
          message={error instanceof Error ? error.message : "Failed to load board"}
        />
      ) : null}
      {message ? <Typography color="error">{message}</Typography> : null}

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" } }}>
        {pins.map((pin) => (
          <ActionPinButton
            key={pin.pin_id}
            pin={pin}
            running={runningId === pin.pin_id}
            onRun={(item) => void runAction(item)}
            onSchedule={(item) => setScheduleSkill(item.id)}
          />
        ))}
      </Box>

      <ActionResultPanel run={lastRun} onRunAgain={() => lastRun && void runAction({ pin_id: lastRun.run_id, type: lastRun.source_type as ActionPin["type"], id: lastRun.source_id, label: lastRun.source_id })} />

      <Box sx={{ display: "grid", gap: 2 }}>
        <Typography variant="h6">All actions</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 180px" } }}>
          <TextField label="Search actions" value={query} onChange={(event) => setQuery(event.target.value)} />
          <TextField select label="Type" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            {["all", "skill", "playbook", "agent_app"].map((value) => (
              <MenuItem key={value} value={value}>{value === "all" ? "All" : value}</MenuItem>
            ))}
          </TextField>
        </Box>
        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Action</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Run</TableCell>
                <TableCell align="right">Pin</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {actions.map((action) => {
                const runnable = action.type === "skill" || action.type === "playbook" || action.type === "agent_app";
                return (
                  <TableRow key={`${action.type}:${action.id}`} hover>
                    <TableCell>
                      <Typography variant="body2">{action.label}</Typography>
                      <Typography variant="caption" color="text.secondary">{action.id}</Typography>
                    </TableCell>
                    <TableCell><Chip size="small" label={action.type} /></TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        disabled={!runnable || Boolean(runningId)}
                        startIcon={<PlayArrowIcon fontSize="small" />}
                        onClick={() => void runAction({ pin_id: `${action.type}:${action.id}`, type: action.type as ActionPin["type"], id: action.id, label: action.label })}
                      >
                        Run
                      </Button>
                    </TableCell>
                    <TableCell align="right">
                      <Button size="small" startIcon={<AddIcon fontSize="small" />} onClick={() => void addPin(action)} disabled={!runnable}>
                        Pin
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      </Box>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button href="/chat" variant="outlined">Chat</Button>
        <Button href="/documents" variant="outlined">Documents</Button>
        <Button href="/playbooks/studio/new" variant="outlined">Playbooks studio</Button>
        <Button href="/admin/cron" variant="outlined">Cron</Button>
      </Box>
      <AgentOsMoreLinks />
      <ActionScheduleDialog
        skillSlug={scheduleSkill}
        open={Boolean(scheduleSkill)}
        onClose={() => setScheduleSkill(null)}
        onScheduled={(text) => {
          setMessage(text);
          void mutate();
        }}
      />
    </Box>
  );
}

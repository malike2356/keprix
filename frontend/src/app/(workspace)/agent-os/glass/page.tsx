"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import AgentOsMoreLinks from "@/components/agent-os/AgentOsMoreLinks";
import { AGENT_OS_HUB_HOME } from "@/components/agent-os/AgentOsSubnav";
import ShipDefaultsPanel from "@/components/agent-os/ShipDefaultsPanel";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/loading";
import UsagePeriodToolbar from "@/components/usage/UsagePeriodToolbar";
import { ceApi } from "@/lib/ce-api";
import {
  readStoredUsagePeriod,
  storeUsagePeriod,
  USAGE_PERIOD_OPTIONS,
  type UsagePeriodDays,
} from "@/lib/usage-api";
import { formatTokenCount, formatUsdCost } from "@/lib/usage-format";

type GlassPayload = {
  ok: boolean;
  days: number;
  agents: {
    installed_count: number;
    catalog_count: number;
    installed: Array<{ name?: string; display_name?: string; runtime?: string }>;
    catalog_featured: Array<{ id?: string; display_name?: string; category?: string }>;
  };
  memory: {
    configured: boolean;
    root_path: string;
    graph_nodes: number;
    graph_edges: number;
    error?: string;
  };
  tasks: {
    board_count: number;
    todo: number;
    doing: number;
    done: number;
    workflow_boards: Array<{ id: string; title: string; workflow: string }>;
  };
  tokens: {
    summary: {
      request_count?: number;
      total_tokens?: number;
      total_cost_usd?: number;
    };
    by_agent: Array<{
      key: string;
      label: string;
      request_count: number;
      total_tokens: number;
      total_cost_usd: number;
    }>;
    efficiency: Array<{
      key: string;
      label: string;
      tokens_per_request: number;
      cost_per_1k_tokens: number;
      request_count: number;
    }>;
    error?: string;
  };
  links: Record<string, string>;
};

function coercePeriod(raw: string | null | undefined): UsagePeriodDays {
  const n = Number(raw);
  if (USAGE_PERIOD_OPTIONS.includes(n as UsagePeriodDays)) return n as UsagePeriodDays;
  return readStoredUsagePeriod();
}

async function fetchGlass(days: number): Promise<GlassPayload> {
  const response = await ceApi(`/api/agent-os/glass?days=${days}`);
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as GlassPayload;
}

function Panel({
  title,
  children,
  href,
  hrefLabel = "Open",
}: {
  title: string;
  children: React.ReactNode;
  href?: string;
  hrefLabel?: string;
}) {
  return (
    <Paper
      variant="outlined"
      className="agent-os-glass-panel"
      sx={{
        p: 2,
        height: "100%",
        bgcolor: "background.paper",
        backdropFilter: "blur(10px)",
        backgroundImage: "linear-gradient(160deg, rgba(255,255,255,0.06), transparent 50%)",
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          {title}
        </Typography>
        {href ? (
          <Button component="a" href={href} size="small">
            {hrefLabel}
          </Button>
        ) : null}
      </Stack>
      {children}
    </Paper>
  );
}

export default function AgentOsGlassPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [periodDays, setPeriodDays] = React.useState<UsagePeriodDays>(7);

  React.useEffect(() => {
    setPeriodDays(coercePeriod(searchParams.get("days")));
  }, [searchParams]);

  const setPeriod = (days: UsagePeriodDays) => {
    storeUsagePeriod(days);
    setPeriodDays(days);
    const next = new URLSearchParams(searchParams.toString());
    next.set("days", String(days));
    router.replace(`${pathname}?${next.toString()}`);
  };

  const { data, error, isLoading, mutate } = useSWR(`agent-os-glass-${periodDays}`, () => fetchGlass(periodDays));

  return (
    <Box>
      <PageHeader
        title="Agent OS glass"
        description="One pane: agents, memory, tasks, token burn, and ship defaults."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: AGENT_OS_HUB_HOME },
          { label: "Glass" },
        ]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component="a" href={`/usage?days=${periodDays}`} variant="outlined" size="small">
              Full usage
            </Button>
            <Button onClick={() => mutate()} size="small">
              Refresh
            </Button>
          </Stack>
        }
      />

      <UsagePeriodToolbar value={periodDays} onChange={setPeriod} />

      {error ? (
        <ErrorState title="Glass failed to load" message={error.message} onRetry={() => void mutate()} />
      ) : null}
      {isLoading && !data ? (
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
          <SkeletonBlock height={180} />
          <SkeletonBlock height={180} />
          <SkeletonBlock height={180} />
          <SkeletonBlock height={180} />
        </Box>
      ) : null}

      {data ? (
        <>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            }}
          >
            <Panel title="Agents" href={data.links.agent_runtime || "/agent-runtime"}>
              <Stack direction="row" spacing={1} sx={{ mb: 1 }} flexWrap="wrap" useFlexGap>
                <Chip size="small" label={`${data.agents.installed_count} installed`} />
                <Chip size="small" label={`${data.agents.catalog_count} catalog`} variant="outlined" />
              </Stack>
              {(data.agents.installed.length ? data.agents.installed : data.agents.catalog_featured)
                .slice(0, 6)
                .map((item) => {
                  const key =
                    ("name" in item && item.name) ||
                    ("id" in item && item.id) ||
                    item.display_name ||
                    "agent";
                  const meta =
                    ("runtime" in item && item.runtime) || ("category" in item && item.category) || "";
                  return (
                    <Typography key={String(key)} variant="body2" sx={{ mb: 0.5 }}>
                      {item.display_name || key}
                      {meta ? (
                        <Typography component="span" variant="caption" color="text.secondary">
                          {" "}
                          · {meta}
                        </Typography>
                      ) : null}
                    </Typography>
                  );
                })}
            </Panel>

            <Panel title="Memory" href={data.links.memory_galaxy || "/memory/galaxy"}>
              {data.memory.error ? (
                <Typography color="error" variant="body2" sx={{ mb: 1 }}>
                  {data.memory.error}
                </Typography>
              ) : null}
              <Stack direction="row" spacing={1} sx={{ mb: 1 }} flexWrap="wrap" useFlexGap>
                <Chip
                  size="small"
                  color={data.memory.configured ? "success" : "default"}
                  label={data.memory.configured ? "Vault ready" : "Vault unset"}
                />
                <Chip size="small" label={`${data.memory.graph_nodes} notes`} />
                <Chip size="small" label={`${data.memory.graph_edges} links`} variant="outlined" />
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ wordBreak: "break-all" }}>
                {data.memory.root_path || "Default vault will be created on first capture."}
              </Typography>
            </Panel>

            <Panel title="Tasks" href={data.links.tasks || "/tasks"} hrefLabel="Open tasks">
              <Stack direction="row" spacing={1} sx={{ mb: 1 }} flexWrap="wrap" useFlexGap>
                <Chip size="small" label={`${data.tasks.todo} todo`} />
                <Chip size="small" label={`${data.tasks.doing} doing`} />
                <Chip size="small" label={`${data.tasks.done} done`} color="success" />
              </Stack>
              {data.tasks.workflow_boards.slice(0, 5).map((board) => (
                <Typography key={board.id} variant="body2" sx={{ mb: 0.5 }}>
                  <Link href={`/agent-os?board=${encodeURIComponent(board.id)}`}>{board.title}</Link>{" "}
                  <Typography component="span" variant="caption" color="text.secondary">
                    ({board.workflow})
                  </Typography>
                </Typography>
              ))}
              {!data.tasks.workflow_boards.length ? (
                <EmptyState
                  title="No workflow boards yet"
                  description="Run a content-series workflow, then open Tasks or the action board."
                />
              ) : null}
              <Button component="a" href={data.links.board || "/agent-os"} size="small" sx={{ mt: 1 }}>
                Action board
              </Button>
            </Panel>

            <Panel title={`Tokens (${periodDays}d)`} href={`/usage?days=${periodDays}`}>
              {data.tokens.error ? (
                <Typography color="error" variant="body2" sx={{ mb: 1 }}>
                  {data.tokens.error}
                </Typography>
              ) : null}
              <Stack direction="row" spacing={1} sx={{ mb: 1 }} flexWrap="wrap" useFlexGap>
                <Chip size="small" label={formatTokenCount(data.tokens.summary.total_tokens ?? 0)} />
                <Chip size="small" label={formatUsdCost(data.tokens.summary.total_cost_usd ?? 0)} />
                <Chip
                  size="small"
                  variant="outlined"
                  label={`${data.tokens.summary.request_count ?? 0} requests`}
                />
              </Stack>
              {data.tokens.by_agent.length ? (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Agent</TableCell>
                      <TableCell align="right">Tokens</TableCell>
                      <TableCell align="right">Cost</TableCell>
                      <TableCell align="right">Tok/req</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.tokens.by_agent.slice(0, 6).map((row) => {
                      const efficiency = data.tokens.efficiency.find((item) => item.key === row.key);
                      return (
                        <TableRow key={row.key}>
                          <TableCell>{row.label}</TableCell>
                          <TableCell align="right">{formatTokenCount(row.total_tokens)}</TableCell>
                          <TableCell align="right">{formatUsdCost(row.total_cost_usd)}</TableCell>
                          <TableCell align="right">{efficiency?.tokens_per_request ?? ";"}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              ) : (
                <EmptyState
                  title="No usage yet"
                  description="Agent breakdown appears after LLM calls with agent metadata."
                />
              )}
            </Panel>
          </Box>

          <ShipDefaultsPanel />
          <AgentOsMoreLinks />
        </>
      ) : null}
    </Box>
  );
}

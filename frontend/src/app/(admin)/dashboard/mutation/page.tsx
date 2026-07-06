"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Drawer from "@mui/material/Drawer";
import LinearProgress from "@mui/material/LinearProgress";
import Tab from "@mui/material/Tab";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import {
  IconCheck,
  IconChevronDown,
  IconChevronUp,
  IconMinus,
  IconX,
} from "@tabler/icons-react";
import * as React from "react";
import { useSearchParams } from "next/navigation";
import PageContainer from "@/components/shared/PageContainer";
import CompoundingMetricsCard from "@/components/mutation/CompoundingMetricsCard";
import DiffViewer from "@/components/mutation/DiffViewer";
import GeneratedToolCard from "@/components/mutation/GeneratedToolCard";
import MutationApprovalPanel from "@/components/mutation/MutationApprovalPanel";
import MutationHistoryTable from "@/components/mutation/MutationHistoryTable";
import MutationQualityBadge from "@/components/mutation/MutationQualityBadge";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import {
  activatePromptVersion,
  approveMutation,
  fetchCodeDiff,
  fetchCodeTestOutput,
  fetchQualityHistory,
  fetchToolSource,
  rollbackMutation,
  useCodeMutations,
  useCompoundingMetrics,
  useGeneratedTools,
  useMutationHistory,
  useMutationQueue,
  useMutationStats,
  usePromptVersions,
  type MutationHistoryFilters,
  type MutationRecord,
  type PromptVersion,
} from "@/lib/mutation-api";
import { formatTimeAgo } from "@/lib/time-ago";

type TabId = "pending" | "tools" | "prompts" | "code" | "history";

const TIER_COLORS: Record<string, "primary" | "secondary" | "info"> = {
  tool: "primary",
  prompt: "secondary",
  code: "info",
};

function confidenceFromRecord(record: MutationRecord): string {
  const value = record.metadata?.confidence;
  if (typeof value === "number") return `${Math.round(value * 100)}%`;
  if (record.quality_score !== null) return `${Math.round(record.quality_score * 100)}%`;
  return "N/A";
}

export default function MutationGovernancePage() {
  const searchParams = useSearchParams();
  const [tab, setTab] = React.useState<TabId>("pending");
  const toolsPage = 1;
  const codePage = 1;
  const [historyFilters, setHistoryFilters] = React.useState<MutationHistoryFilters>({ page: 1, perPage: 20 });
  const [expandedId, setExpandedId] = React.useState<string | null>(null);
  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [bulkProgress, setBulkProgress] = React.useState<number | null>(null);
  const [sourceDrawer, setSourceDrawer] = React.useState<{ id: string; source: string; name: string } | null>(null);
  const [qualitySamples, setQualitySamples] = React.useState<number[]>([]);
  const [mergeTarget, setMergeTarget] = React.useState<MutationRecord | null>(null);
  const [promptDiff, setPromptDiff] = React.useState<{ before: string; after: string } | null>(null);

  const { data: stats } = useMutationStats();
  const { data: compounding } = useCompoundingMetrics();
  const { data: queue, mutate: refreshQueue } = useMutationQueue();
  const { data: tools, mutate: refreshTools } = useGeneratedTools(toolsPage);
  const { data: prompts, mutate: refreshPrompts } = usePromptVersions();
  const { data: codeItems, mutate: refreshCode } = useCodeMutations(codePage);
  const { data: history, mutate: refreshHistory } = useMutationHistory(historyFilters);

  const pendingItems = queue?.items ?? [];
  const pendingCount = stats?.staged ?? pendingItems.length;

  React.useEffect(() => {
    if (searchParams.get("status") === "staged") {
      setTab("pending");
    }
  }, [searchParams]);

  const refreshAll = React.useCallback(() => {
    void refreshQueue();
    void refreshTools();
    void refreshPrompts();
    void refreshCode();
    void refreshHistory();
  }, [refreshQueue, refreshTools, refreshPrompts, refreshCode, refreshHistory]);

  const toggleSelected = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  const runBulk = async (action: "approve" | "reject") => {
    const targets = pendingItems.filter((item) => selectedIds.includes(item.id));
    setBulkProgress(0);
    for (let index = 0; index < targets.length; index += 1) {
      const item = targets[index];
      if (action === "approve") {
        await approveMutation(item.id, item.tier, item.tier === "prompt" ? item.name : undefined);
      } else {
        await approveMutation(item.id, item.tier); // reject uses separate - fix below
      }
      setBulkProgress(Math.round(((index + 1) / targets.length) * 100));
    }
    setSelectedIds([]);
    setBulkProgress(null);
    refreshAll();
  };

  const runBulkReject = async () => {
    const targets = pendingItems.filter((item) => selectedIds.includes(item.id));
    setBulkProgress(0);
    for (let index = 0; index < targets.length; index += 1) {
      const item = targets[index];
      const { rejectMutation } = await import("@/lib/mutation-api");
      await rejectMutation(item.id, item.tier, "Bulk rejected");
      setBulkProgress(Math.round(((index + 1) / targets.length) * 100));
    }
    setSelectedIds([]);
    setBulkProgress(null);
    refreshAll();
  };

  const openToolSource = async (id: string) => {
    const [source, quality] = await Promise.all([
      fetchToolSource(id),
      fetchQualityHistory(id),
    ]);
    setSourceDrawer({ id, source: source.source_code, name: source.name });
    setQualitySamples(quality.samples.map((sample) => sample.score).reverse());
  };

  const groupedPrompts = React.useMemo(() => {
    const groups = new Map<string, PromptVersion[]>();
    for (const version of prompts?.items ?? []) {
      const list = groups.get(version.prompt_key) ?? [];
      list.push(version);
      groups.set(version.prompt_key, list);
    }
    for (const list of groups.values()) {
      list.sort((a, b) => b.version - a.version);
    }
    return Array.from(groups.entries());
  }, [prompts?.items]);

  return (
    <PageContainer
      title="Mutation governance"
      description="Review, approve, and roll back deployment-specific mutations."
      padded={false}
    >
      <Box sx={{ display: "grid", gap: 2, mb: 2 }}>
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", xl: "repeat(4, 1fr)" },
          }}
        >
          <CompoundingMetricsCard metrics={compounding} compact />
          <StatMini label="Pending approvals" value={pendingCount} />
          <StatMini label="Active tools" value={stats?.active_tools ?? 0} />
          <StatMini label="Evolved prompts" value={stats?.evolved_prompts ?? 0} />
        </Box>
      </Box>

      <Tabs value={tab} onChange={(_, value: TabId) => setTab(value)} sx={{ mb: 2 }}>
        <Tab value="pending" label={`Pending (${pendingCount})`} />
        <Tab value="tools" label="Tools" />
        <Tab value="prompts" label="Prompts" />
        <Tab value="code" label="Code" />
        <Tab value="history" label="History" />
      </Tabs>

      {bulkProgress !== null ? <LinearProgress variant="determinate" value={bulkProgress} sx={{ mb: 2 }} /> : null}

      {tab === "pending" ? (
        <Box sx={{ display: "grid", gap: 2 }}>
          {selectedIds.length > 0 ? (
            <Box sx={{ display: "flex", gap: 1 }}>
              <Button size="small" variant="contained" color="success" onClick={() => void runBulk("approve")}>
                Bulk approve ({selectedIds.length})
              </Button>
              <Button size="small" color="inherit" onClick={() => void runBulkReject()}>
                Bulk reject ({selectedIds.length})
              </Button>
            </Box>
          ) : null}
          {pendingItems.length === 0 ? (
            <Alert severity="success">No mutations awaiting approval.</Alert>
          ) : (
            pendingItems.map((item) => {
              const expanded = expandedId === item.id;
              return (
                <Box key={item.id} sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: 2 }}>
                  <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                    <Checkbox
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleSelected(item.id)}
                    />
                    <Chip size="small" label={item.tier.toUpperCase()} color={TIER_COLORS[item.tier] ?? "default"} />
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      {item.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.trigger}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Confidence {confidenceFromRecord(item)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatTimeAgo(item.recorded_at)}
                    </Typography>
                    <Box sx={{ ml: "auto", display: "flex", gap: 1 }}>
                      <Button size="small" onClick={() => setExpandedId(expanded ? null : item.id)}>
                        {expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
                      </Button>
                      <MutationApprovalPanel
                        mutationId={item.id}
                        tier={item.tier}
                        promptKey={item.tier === "prompt" ? item.name : undefined}
                        onApproved={refreshAll}
                        onRejected={refreshAll}
                        compact
                      />
                    </Box>
                  </Box>
                  <Collapse in={expanded}>
                    <Box sx={{ mt: 2 }}>
                      {item.tier === "tool" ? (
                        <PendingToolDetail record={item} />
                      ) : null}
                      {item.tier === "prompt" ? (
                        <PromptSideBySide before={String(item.metadata?.before_value ?? "")} after={String(item.after_value ?? item.description ?? "")} />
                      ) : null}
                      {item.tier === "code" ? (
                        <PendingCodeDetail record={item} />
                      ) : null}
                    </Box>
                  </Collapse>
                </Box>
              );
            })
          )}
        </Box>
      ) : null}

      {tab === "tools" ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Quality</TableCell>
              <TableCell>Uses</TableCell>
              <TableCell>Last used</TableCell>
              <TableCell>Age</TableCell>
              <TableCell>Created by</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(tools?.items ?? []).map((item) => (
              <TableRow key={item.id} hover>
                <TableCell>
                  {item.name}
                  {item.metadata?.promoted ? " *" : ""}
                </TableCell>
                <TableCell>
                  <Chip size="small" label={item.status} color={item.status === "approved" ? "success" : item.status === "staged" ? "warning" : "default"} />
                </TableCell>
                <TableCell>
                  <MutationQualityBadge score={item.quality_score} useCount={item.use_count} status={item.status} />
                </TableCell>
                <TableCell>{item.use_count}</TableCell>
                <TableCell>{item.last_used_at ? formatTimeAgo(item.last_used_at) : "never"}</TableCell>
                <TableCell>{formatTimeAgo(item.recorded_at)}</TableCell>
                <TableCell>{item.approved_by || String(item.metadata?.created_by ?? "system")}</TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => void openToolSource(item.id)}>
                    View source
                  </Button>
                  {item.status === "staged" ? (
                    <MutationApprovalPanel mutationId={item.id} tier="tool" onApproved={refreshAll} onRejected={refreshAll} compact />
                  ) : null}
                  {item.status === "approved" ? (
                    <Button
                      size="small"
                      onClick={() => void rollbackMutation(item.id, "tool").then(refreshAll)}
                    >
                      Rollback
                    </Button>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}

      {tab === "prompts" ? (
        <Box sx={{ display: "grid", gap: 2 }}>
          {groupedPrompts.map(([promptKey, versions]) => (
            <Box key={promptKey} sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: 2 }}>
              <Typography variant="h6" sx={{ mb: 1 }}>
                {promptKey}
              </Typography>
              {versions.map((version, index) => {
                const previous = versions[index + 1];
                return (
                  <Box
                    key={version.id}
                    sx={{
                      display: "flex",
                      gap: 1,
                      alignItems: "center",
                      flexWrap: "wrap",
                      py: 0.75,
                      bgcolor: version.is_active ? "action.hover" : "transparent",
                      borderRadius: 1,
                      px: 1,
                    }}
                  >
                    <Typography variant="body2">v{version.version}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {version.created_by}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatTimeAgo(version.created_at)}
                    </Typography>
                    <Chip size="small" label={version.is_active ? "active" : "inactive"} color={version.is_active ? "success" : "default"} />
                    <Button
                      size="small"
                      disabled={!previous}
                      onClick={() =>
                        setPromptDiff({
                          before: previous?.content ?? "",
                          after: version.content,
                        })
                      }
                    >
                      Diff
                    </Button>
                    {!version.is_active ? (
                      <Button
                        size="small"
                        onClick={() => void activatePromptVersion(version.id).then(refreshAll)}
                      >
                        Activate
                      </Button>
                    ) : (
                      <Button
                        size="small"
                        onClick={() => void rollbackMutation(version.id, "prompt", promptKey).then(refreshAll)}
                      >
                        Rollback
                      </Button>
                    )}
                  </Box>
                );
              })}
            </Box>
          ))}
        </Box>
      ) : null}

      {tab === "code" ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Task</TableCell>
              <TableCell>Branch</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Tests</TableCell>
              <TableCell>Files</TableCell>
              <TableCell>Age</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(codeItems?.items ?? []).map((item) => {
              const testsPassed = item.metadata?.test_passed;
              return (
                <TableRow key={item.id} hover>
                  <TableCell>{item.description || item.name}</TableCell>
                  <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>
                    {String(item.metadata?.branch_name ?? "n/a")}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={item.status} color={item.status === "approved" ? "success" : item.status === "staged" ? "warning" : "default"} />
                  </TableCell>
                  <TableCell>
                    {testsPassed === true ? <IconCheck size={16} color="green" /> : null}
                    {testsPassed === false ? <IconX size={16} color="red" /> : null}
                    {testsPassed === undefined || testsPassed === null ? <IconMinus size={16} /> : null}
                  </TableCell>
                  <TableCell>{String(item.metadata?.files_changed ?? "n/a")}</TableCell>
                  <TableCell>{formatTimeAgo(item.recorded_at)}</TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => setMergeTarget(item)}>
                      {item.status === "staged" ? "Approve" : "View"}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      ) : null}

      {tab === "history" ? (
        <MutationHistoryTable
          items={history?.items ?? []}
          filters={historyFilters}
          onFiltersChange={setHistoryFilters}
          page={historyFilters.page ?? 1}
          total={history?.total ?? 0}
          onPageChange={(page) => setHistoryFilters((current) => ({ ...current, page }))}
        />
      ) : null}

      <Drawer anchor="right" open={Boolean(sourceDrawer)} onClose={() => setSourceDrawer(null)}>
        <Box sx={{ width: { xs: "100vw", sm: 520 }, p: 2, display: "grid", gap: 2 }}>
          <Typography variant="h6">{sourceDrawer?.name}</Typography>
          {sourceDrawer ? <CodeBlock language="python" content={sourceDrawer.source} /> : null}
          {qualitySamples.length > 0 ? (
            <GeneratedToolCard
              record={{
                id: sourceDrawer?.id ?? "",
                recorded_at: "",
                workspace_id: "default",
                tier: "tool",
                trigger: "",
                status: "approved",
                name: sourceDrawer?.name ?? "",
                description: null,
                approved_by: null,
                approved_at: null,
                quality_score: qualitySamples[qualitySamples.length - 1] ?? null,
                use_count: qualitySamples.length,
                last_used_at: null,
                metadata: {},
              }}
              qualitySamples={qualitySamples}
              showActions={false}
            />
          ) : null}
        </Box>
      </Drawer>

      <Dialog open={Boolean(mergeTarget)} onClose={() => setMergeTarget(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Merge mutation branch into main?</DialogTitle>
        <DialogContent>
          {mergeTarget ? (
            <Box sx={{ display: "grid", gap: 1 }}>
              <Typography variant="body2">
                Branch: <code>{String(mergeTarget.metadata?.branch_name ?? "unknown")}</code>
              </Typography>
              <Typography variant="body2">
                Files: {String(mergeTarget.metadata?.files_changed ?? "unknown")}
              </Typography>
              <Typography variant="body2">
                Tests:{" "}
                {mergeTarget.metadata?.test_passed === true
                  ? "passed"
                  : mergeTarget.metadata?.test_passed === false
                    ? "failed"
                    : "pending"}
              </Typography>
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMergeTarget(null)}>Cancel</Button>
          <Button
            variant="contained"
            color="success"
            onClick={() => {
              if (!mergeTarget) return;
              void approveMutation(mergeTarget.id, "code").then(() => {
                setMergeTarget(null);
                refreshAll();
              });
            }}
          >
            Merge and Approve
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(promptDiff)} onClose={() => setPromptDiff(null)} maxWidth="lg" fullWidth>
        <DialogTitle>Prompt diff</DialogTitle>
        <DialogContent>
          {promptDiff ? <PromptSideBySide before={promptDiff.before} after={promptDiff.after} /> : null}
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}

function StatMini({ label, value }: { label: string; value: number }) {
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: 2 }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h4" sx={{ fontWeight: 700 }}>
        {value}
      </Typography>
    </Box>
  );
}

function PromptSideBySide({ before, after }: { before: string; after: string }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>
      <Box>
        <Typography variant="overline">Before</Typography>
        <CodeBlock language="markdown" content={before || "(empty)"} />
      </Box>
      <Box>
        <Typography variant="overline">After</Typography>
        <CodeBlock language="markdown" content={after || "(empty)"} />
      </Box>
    </Box>
  );
}

function PendingToolDetail({ record }: { record: MutationRecord }) {
  const [source, setSource] = React.useState<string | null>(null);
  React.useEffect(() => {
    void fetchToolSource(record.id)
      .then((payload) => setSource(payload.source_code))
      .catch(() => setSource(null));
  }, [record.id]);
  return (
    <Box sx={{ display: "grid", gap: 1 }}>
      <Typography variant="body2">
        Sandbox: {record.metadata?.sandbox_passed === false ? "failed" : "passed"}
      </Typography>
      {source ? <CodeBlock language="python" content={source} /> : null}
    </Box>
  );
}

function PendingCodeDetail({ record }: { record: MutationRecord }) {
  const [diff, setDiff] = React.useState<string>("");
  const [testOutput, setTestOutput] = React.useState<string | null>(null);
  const [testPassed, setTestPassed] = React.useState<boolean | null>(null);
  React.useEffect(() => {
    void fetchCodeDiff(record.id)
      .then((payload) => setDiff(payload.diff))
      .catch(() => setDiff(""));
    void fetchCodeTestOutput(record.id)
      .then((payload) => {
        setTestOutput(payload.test_output);
        setTestPassed(payload.test_passed);
      })
      .catch(() => {
        setTestOutput(null);
        setTestPassed(null);
      });
  }, [record.id]);
  return (
    <Box sx={{ display: "grid", gap: 1 }}>
      <Chip
        size="small"
        label={testPassed === true ? "Tests passed" : testPassed === false ? "Tests failed" : "Tests pending"}
        color={testPassed === true ? "success" : testPassed === false ? "error" : "default"}
      />
      {diff ? <DiffViewer diff={diff} /> : null}
      {testOutput ? (
        <Collapse in>
          <CodeBlock language="text" content={testOutput} />
        </Collapse>
      ) : null}
    </Box>
  );
}

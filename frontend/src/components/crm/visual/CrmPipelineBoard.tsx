"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import CrmStatusBadge from "@/components/crm/visual/CrmStatusBadge";
import { CRM_WORKSPACE, stageLabel } from "@/components/crm/types";
import {
  commitCrmStageTransition,
  fetchCrmNextBestAction,
  fetchCrmPipelineBoard,
  previewCrmStageTransition,
} from "@/lib/crm-api";

type CardRow = {
  id: string;
  entity_type?: string;
  title?: string;
  subtitle?: string;
  stage?: string;
  owner?: string | null;
  source?: string | null;
  warnings?: string[];
  deal_value?: number | null;
  last_touch_at?: string | null;
  next_action?: string | null;
  consent_contactability?: string;
  version?: number;
  deep_links?: Record<string, string>;
  fit_score?: unknown;
  engagement_score?: unknown;
};

export default function CrmPipelineBoard() {
  const router = useRouter();
  const search = useSearchParams();
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [selected, setSelected] = React.useState<CardRow | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [mobileMode, setMobileMode] = React.useState<"lanes" | "list">("lanes");
  const [q, setQ] = React.useState(search.get("q") || "");
  const savedView = search.get("view") || "";

  const nba = useSWR(
    selected ? ["crm-nba", CRM_WORKSPACE, selected.id, selected.entity_type] : null,
    () =>
      fetchCrmNextBestAction(
        String(selected?.id),
        CRM_WORKSPACE,
        String(selected?.entity_type || "lead"),
      ),
  );

  const board = useSWR(
    ["crm-pipeline-board", CRM_WORKSPACE, savedView, search.toString()],
    () =>
      fetchCrmPipelineBoard(CRM_WORKSPACE, {
        saved_view: savedView || undefined,
        q: search.get("q") || undefined,
        owner: search.get("owner") || undefined,
        source: search.get("source") || undefined,
        pack: search.get("pack") || undefined,
        stage: search.get("stage") || undefined,
        tag: search.get("tag") || undefined,
        contactability: search.get("contactability") || undefined,
      }),
  );

  const stages = board.data?.stages || [];
  const columns = board.data?.columns || {};

  const pushFilter = (key: string, value: string) => {
    const params = new URLSearchParams(search.toString());
    if (!value) params.delete(key);
    else params.set(key, value);
    router.push(`/crm/pipeline?${params.toString()}`);
  };

  const applySearch = () => pushFilter("q", q.trim());

  const moveCard = async (card: CardRow, toStage: string, humanConfirmed = false) => {
    setBusyId(card.id);
    setError(null);
    const entityType = card.entity_type || "lead";
    try {
      const preview = await previewCrmStageTransition(
        {
          entity_type: entityType,
          entity_id: card.id,
          to_stage: toStage,
          expected_version: card.version,
          human_confirmed: humanConfirmed,
        },
        CRM_WORKSPACE,
      );
      if (!preview.allowed) {
        setError(
          `${String(preview.reason_code || "blocked")}. ${String(preview.safe_next || "Transition denied.")}`,
        );
        return;
      }
      const result = await commitCrmStageTransition(
        {
          entity_type: entityType,
          entity_id: card.id,
          to_stage: toStage,
          expected_version: card.version,
          human_confirmed: humanConfirmed,
        },
        CRM_WORKSPACE,
      );
      if (result.blocked) {
        setError("Soft Wall approval required before this stage move.");
        return;
      }
      if (!result.ok) {
        setError(String(result.reason_code || "Transition failed"));
        return;
      }
      setMessage(`Moved to ${stageLabel(toStage)}`);
      setSelected(null);
      await board.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Move failed");
    } finally {
      setBusyId(null);
    }
  };

  const onDragStart = (event: React.DragEvent, card: CardRow) => {
    event.dataTransfer.setData("application/crm-card", JSON.stringify(card));
    event.dataTransfer.effectAllowed = "move";
  };

  const onDropLane = async (event: React.DragEvent, stage: string) => {
    event.preventDefault();
    const raw = event.dataTransfer.getData("application/crm-card");
    if (!raw) return;
    try {
      const card = JSON.parse(raw) as CardRow;
      if (card.stage === stage) return;
      await moveCard(card, stage);
    } catch {
      setError("Could not read dragged card");
    }
  };

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1} alignItems={{ md: "center" }} justifyContent="space-between">
        <Box>
          <Typography variant="h6">Pipeline board</Typography>
          <Typography variant="body2" color="text.secondary">
            Canonical CRM stages with Soft Wall gates. Tables remain at{" "}
            <Typography component="a" href="/crm/leads" color="primary" variant="body2">
              /crm/leads
            </Typography>
            .
          </Typography>
        </Box>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={mobileMode}
          onChange={(_, v) => v && setMobileMode(v)}
          aria-label="Board layout mode"
        >
          <ToggleButton value="lanes">Lanes</ToggleButton>
          <ToggleButton value="list">Stage list</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
        <TextField
          size="small"
          label="Search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && applySearch()}
          sx={{ minWidth: 180 }}
        />
        <Button size="small" variant="outlined" onClick={applySearch}>
          Apply
        </Button>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="saved-view">Saved view</InputLabel>
          <Select
            labelId="saved-view"
            label="Saved view"
            value={savedView}
            onChange={(e) => pushFilter("view", e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            {(board.data?.saved_views || []).map((v) => (
              <MenuItem key={String(v.id)} value={String(v.id)}>
                {String(v.label || v.id)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="caption" color="text.secondary">
          {board.data?.totals?.cards ?? 0} cards
        </Typography>
      </Stack>

      {board.isLoading && !board.data ? (
        <Typography color="text.secondary">Loading pipeline...</Typography>
      ) : mobileMode === "list" ? (
        <Stack spacing={2}>
          {stages.map((stage) => {
            const cards = (columns[stage] || []) as CardRow[];
            return (
              <Box key={stage} component="section" aria-labelledby={`lane-${stage}`}>
                <Typography id={`lane-${stage}`} variant="subtitle2" gutterBottom>
                  {stageLabel(stage)} ({cards.length})
                </Typography>
                <Stack spacing={1}>
                  {cards.length === 0 ? (
                    <Typography variant="caption" color="text.secondary">
                      Empty
                    </Typography>
                  ) : (
                    cards.map((card) => (
                      <Card key={card.id} variant="outlined">
                        <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                          <Button size="small" onClick={() => setSelected(card)}>
                            {card.title}
                          </Button>
                          <Typography variant="caption" display="block" color="text.secondary">
                            {card.subtitle || card.source || "No detail"}
                          </Typography>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </Stack>
              </Box>
            );
          })}
        </Stack>
      ) : (
        <Box
          sx={{
            display: "flex",
            gap: 1.5,
            overflowX: "auto",
            pb: 1,
            minHeight: 420,
          }}
          role="list"
          aria-label="Pipeline lanes"
        >
          {stages.map((stage) => {
            const cards = (columns[stage] || []) as CardRow[];
            const lane = (board.data?.lanes || []).find((l) => l.stage === stage);
            return (
              <Card
                key={stage}
                variant="outlined"
                role="listitem"
                aria-labelledby={`lane-h-${stage}`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => void onDropLane(e, stage)}
                sx={{ minWidth: 240, maxWidth: 280, flex: "0 0 auto", display: "flex", flexDirection: "column" }}
              >
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 }, flex: 1 }}>
                  <Typography id={`lane-h-${stage}`} variant="subtitle2" component="h3" gutterBottom>
                    {stageLabel(stage)} ({Number(lane?.count ?? cards.length)})
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                    avg age {lane?.average_age_hours != null ? `${lane.average_age_hours}h` : "-"}
                    {lane?.truncated ? " · truncated" : ""}
                  </Typography>
                  <Stack spacing={1}>
                    {cards.length === 0 ? (
                      <Typography variant="caption" color="text.secondary" sx={{ py: 2, textAlign: "center" }}>
                        Empty
                      </Typography>
                    ) : (
                      cards.map((card) => (
                        <Box
                          key={card.id}
                          draggable
                          onDragStart={(e) => onDragStart(e, card)}
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setSelected(card);
                            }
                          }}
                          onClick={() => setSelected(card)}
                          sx={{
                            border: 1,
                            borderColor: "divider",
                            borderRadius: 1,
                            p: 1,
                            cursor: "pointer",
                            "&:focus-visible": { outline: "2px solid", outlineColor: "primary.main" },
                          }}
                          aria-label={`${card.title}, stage ${stageLabel(card.stage)}`}
                        >
                          <Typography variant="body2" fontWeight={600} noWrap>
                            {card.title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" display="block" noWrap>
                            {card.subtitle || card.source || "No detail"}
                          </Typography>
                          <Stack direction="row" spacing={0.5} sx={{ mt: 0.75 }} flexWrap="wrap" useFlexGap>
                            {(card.warnings || []).map((w) => (
                              <CrmStatusBadge key={w} state={w === "suppressed" ? "suppressed" : w === "human_owned" ? "approval_required" : "waiting"} />
                            ))}
                          </Stack>
                        </Box>
                      ))
                    )}
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}

      <Drawer
        anchor="right"
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        onKeyDown={(e) => {
          if (!selected) return;
          const idx = stages.indexOf(String(selected.stage || ""));
          if (e.key === "ArrowLeft" && idx > 0) {
            e.preventDefault();
            void moveCard(selected, stages[idx - 1]);
          }
          if (e.key === "ArrowRight" && idx >= 0 && idx < stages.length - 1) {
            e.preventDefault();
            void moveCard(selected, stages[idx + 1]);
          }
        }}
      >
        <Box sx={{ width: { xs: "100vw", sm: 360 }, p: 2 }} role="dialog" aria-label="Card inspector">
          {selected ? (
            <Stack spacing={1.5}>
              <Typography variant="h6">{selected.title}</Typography>
              <Typography variant="body2" color="text.secondary">
                {selected.subtitle || "No company"}
              </Typography>
              <CrmStatusBadge state={selected.stage} />
              <Divider />
              <Typography variant="caption" color="text.secondary">
                Owner: {selected.owner || "-"} · Source: {selected.source || "-"}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Contactability: {selected.consent_contactability || "unknown"}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Last touch: {selected.last_touch_at || "-"}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Next action: {selected.next_action || "-"}
              </Typography>
              {nba.data?.action ? (
                <Alert severity={nba.data.requires_approval ? "warning" : "info"} sx={{ py: 0.5 }}>
                  Next best: {nba.data.action}
                  {nba.data.lifecycle_label ? ` (${nba.data.lifecycle_label})` : ""}
                  {" · "}
                  {nba.data.reason}
                  {nba.data.requires_approval ? " · Soft Wall required" : ""}
                  {typeof nba.data.confidence === "number"
                    ? ` · conf ${Math.round(nba.data.confidence * 100)}%`
                    : ""}
                </Alert>
              ) : null}
              <Typography variant="caption" color="text.secondary">
                Fit / engagement: {String(selected.fit_score ?? "-")} / {String(selected.engagement_score ?? "-")}
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Button size="small" component="a" href={selected.deep_links?.record || `/crm/leads/${selected.id}`}>
                  Full record
                </Button>
                <Button size="small" component="a" href="/crm">
                  Approvals
                </Button>
                <Button size="small" component="a" href="/crm/analytics">
                  Analytics
                </Button>
              </Stack>
              <FormControl size="small" fullWidth>
                <InputLabel id="move-stage">Move stage</InputLabel>
                <Select
                  labelId="move-stage"
                  label="Move stage"
                  value={selected.stage || ""}
                  disabled={busyId === selected.id}
                  onChange={(e) => void moveCard(selected, e.target.value)}
                >
                  {stages.map((s) => (
                    <MenuItem key={s} value={s}>
                      {stageLabel(s)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Stack direction="row" spacing={1}>
                <Button
                  size="small"
                  disabled={busyId === selected.id || stages.indexOf(String(selected.stage || "")) <= 0}
                  onClick={() => {
                    const idx = stages.indexOf(String(selected.stage || ""));
                    if (idx > 0) void moveCard(selected, stages[idx - 1]);
                  }}
                >
                  Previous stage
                </Button>
                <Button
                  size="small"
                  disabled={
                    busyId === selected.id ||
                    stages.indexOf(String(selected.stage || "")) < 0 ||
                    stages.indexOf(String(selected.stage || "")) >= stages.length - 1
                  }
                  onClick={() => {
                    const idx = stages.indexOf(String(selected.stage || ""));
                    if (idx >= 0 && idx < stages.length - 1) void moveCard(selected, stages[idx + 1]);
                  }}
                >
                  Next stage
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                Keyboard: open inspector then use Previous/Next stage (same Soft Wall rules as drag). ArrowLeft /
                ArrowRight also move when the inspector is focused.
              </Typography>
            </Stack>
          ) : null}
        </Box>
      </Drawer>
    </Stack>
  );
}

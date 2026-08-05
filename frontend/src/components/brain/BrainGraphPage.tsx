"use client";

import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useSearchParams } from "next/navigation";
import { SkeletonText } from "@/components/ui/loading";
import BrainFilterBar from "@/components/brain/BrainFilterBar";
import BrainFocusBanner from "@/components/brain/BrainFocusBanner";
import BrainActivationTimeline from "@/components/brain/BrainActivationTimeline";
import BrainGraphCanvas from "@/components/brain/BrainGraphCanvas";
import BrainReplayTransport from "@/components/brain/BrainReplayTransport";
import BrainSessionPicker from "@/components/brain/BrainSessionPicker";
import BrainShareModal from "@/components/brain/BrainShareModal";
import LiveSessionSelector from "@/components/brain/LiveSessionSelector";
import NodeContentPanel from "@/components/brain/NodeContentPanel";
import BrainSectionTabs from "@/components/memory/BrainSectionTabs";
import type { Edge } from "@xyflow/react";
import { buildContributionPath } from "@/components/brain/BrainPathHighlight";
import { apiToFlowEdges, nodeKey } from "@/components/brain/graph-transform";
import { useBrainActivation } from "@/hooks/useBrainActivation";
import { ALL_KINDS, useBrainFilters } from "@/hooks/useBrainFilters";
import { useBrainReplay } from "@/hooks/useBrainReplay";
import { useFocusMode } from "@/hooks/useFocusMode";
import { ceApi } from "@/lib/ce-api";
import type { BrainGraphData, BrainNodeKind, GraphNode } from "@/types/brain-graph";
import type { SessionReplayData } from "@/types/brain-replay";

export default function BrainGraphPage() {
  const searchParams = useSearchParams();
  const [mounted, setMounted] = React.useState(false);
  const [selected, setSelected] = React.useState<GraphNode | null>(null);
  const [liveSessionId, setLiveSessionId] = React.useState("");
  const [matches, setMatches] = React.useState<Array<{ id: string; kind: BrainNodeKind; label: string; excerpt: string }>>([]);
  const [replayData, setReplayData] = React.useState<SessionReplayData | null>(null);
  const [replayFocusedIds, setReplayFocusedIds] = React.useState<Set<string>>(new Set());
  const [pathEdgeIds, setPathEdgeIds] = React.useState<Set<string>>(new Set());
  const [replayEdges, setReplayEdges] = React.useState<Edge[]>([]);
  const [savedSessionFilter, setSavedSessionFilter] = React.useState<string>("");
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  const [activityOpen, setActivityOpen] = React.useState(false);
  const filters = useBrainFilters();
  const focus = useFocusMode();
  const activation = useBrainActivation(replayData ? null : liveSessionId || null);
  const replay = useBrainReplay(replayData);
  const [healthOverlay, setHealthOverlay] = React.useState(false);
  const [shareOpen, setShareOpen] = React.useState(false);
  const highlightedIds = React.useMemo(() => new Set(matches.map((match) => nodeKey(match.kind, match.id))), [matches]);
  const deepLinkHandled = React.useRef(false);

  const replaySessionNodeId = replayData ? nodeKey("session", replayData.session_id) : null;
  const activeFilterCount =
    filters.kinds.length !== ALL_KINDS.length || filters.range !== "all" || Boolean(filters.query) || Boolean(filters.sessionId)
      ? 1
      : 0;

  React.useEffect(() => {
    setMounted(true);
  }, []);

  React.useEffect(() => {
    if (!mounted || deepLinkHandled.current) return;
    const kind = searchParams.get("kind") as BrainNodeKind | null;
    const id = searchParams.get("id");
    if (!kind || !id) return;
    deepLinkHandled.current = true;
    void ceApi(`/api/brain/graph/node/${encodeURIComponent(kind)}/${encodeURIComponent(id)}`)
      .then(async (response) => {
        if (!response.ok) return;
        const node = (await response.json()) as GraphNode;
        setSelected(node);
        focus.focusNode(node);
      })
      .catch(() => undefined);
  }, [mounted, searchParams, focus]);

  React.useEffect(() => {
    if (!replayData) return;
    let cancelled = false;
    ceApi(`/api/brain/graph?session_id=${encodeURIComponent(replayData.session_id)}`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Failed to load session graph");
        const graph = (await response.json()) as BrainGraphData;
        if (!cancelled) {
          setReplayFocusedIds(new Set(graph.nodes.map((node) => nodeKey(node.kind, node.id))));
          setReplayEdges(apiToFlowEdges(graph.edges));
        }
      })
      .catch(() => {
        if (!cancelled) setReplayFocusedIds(new Set([replaySessionNodeId!]));
      });
    return () => {
      cancelled = true;
    };
  }, [replayData, replaySessionNodeId]);

  React.useEffect(() => {
    if (liveSessionId || activation.recentActivations.length > 0) setActivityOpen(true);
  }, [activation.recentActivations.length, liveSessionId]);

  const startReplay = (data: SessionReplayData) => {
    setSavedSessionFilter(filters.sessionId);
    filters.setSessionId(data.session_id);
    setLiveSessionId("");
    setReplayData(data);
    setPathEdgeIds(new Set());
    setReplayEdges([]);
  };

  const closeReplay = () => {
    replay.close();
    setReplayData(null);
    setReplayFocusedIds(new Set());
    setPathEdgeIds(new Set());
    setReplayEdges([]);
    filters.setSessionId(savedSessionFilter);
  };

  const handleReplayNodeSelect = (node: GraphNode) => {
    if (!replayData || replay.playing) return;
    const sessionId = nodeKey("session", replayData.session_id);
    const path = buildContributionPath(replayEdges, sessionId, nodeKey(node.kind, node.id));
    setPathEdgeIds(new Set(path));
    setSelected(node);
  };

  const navigateToNode = React.useCallback(
    (kind: string, id: string) => {
      void ceApi(`/api/brain/graph/node/${encodeURIComponent(kind)}/${encodeURIComponent(id)}`)
        .then(async (response) => {
          if (!response.ok) return;
          const node = (await response.json()) as GraphNode;
          setSelected(node);
          focus.focusNode(node);
          if (typeof window !== "undefined") {
            const url = new URL(window.location.href);
            url.searchParams.set("kind", kind);
            url.searchParams.set("id", id);
            window.history.replaceState({}, "", url.toString());
          }
        })
        .catch(() => undefined);
    },
    [focus],
  );

  if (!mounted) {
    return (
      <Box sx={{ height: "calc(100vh - 96px)", display: "grid", gap: 1 }}>
        <SkeletonText lines={8} />
      </Box>
    );
  }

  return (
    <Box sx={{ height: "calc(100vh - 96px)", display: "flex", flexDirection: "column", minHeight: 0 }}>
      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        sx={{ minHeight: 40, borderBottom: 1, borderColor: "divider", pr: 0.5 }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 600, letterSpacing: -0.2, pl: 0.25, mr: 0.5 }}>
          Brain
        </Typography>
        <Box sx={{ flex: 1, minWidth: 0, "& > *": { mb: "0 !important", borderBottom: "0 !important" } }}>
          <BrainSectionTabs value="graph" />
        </Box>
        <Stack direction="row" spacing={0.5} alignItems="center" sx={{ flexShrink: 0 }}>
          <IconButton
            size="small"
            aria-label={filtersOpen ? "Hide filters" : "Show filters"}
            onClick={() => setFiltersOpen((open) => !open)}
            sx={{ color: "text.secondary" }}
          >
            {filtersOpen ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
          {activeFilterCount ? <Chip size="small" label="Filtered" sx={{ height: 22 }} /> : null}
          <BrainSessionPicker onSelect={startReplay} disabled={Boolean(replayData)} />
          {!replayData ? (
            <>
              <LiveSessionSelector compact sessionId={liveSessionId} onSessionId={setLiveSessionId} />
              <Chip
                size="small"
                variant="outlined"
                color={liveSessionId ? "success" : "default"}
                label={liveSessionId ? "Live" : "Static"}
                sx={{ height: 22 }}
              />
            </>
          ) : (
            <Chip size="small" color="info" label={replayData.session_title} sx={{ height: 22, maxWidth: 140 }} />
          )}
        </Stack>
      </Stack>

      <Collapse in={filtersOpen} unmountOnExit>
        <Box sx={{ px: 0.25, borderBottom: 1, borderColor: "divider" }}>
          <BrainFilterBar
            kinds={filters.kinds}
            setKinds={filters.setKinds}
            range={filters.range}
            setRange={filters.setRange}
            sessionId={filters.sessionId}
            setSessionId={filters.setSessionId}
            query={filters.query}
            setQuery={filters.setQuery}
            showSessionFilters={false}
            clear={() => {
              filters.clear();
              setMatches([]);
              focus.clearFocus();
            }}
            onResults={setMatches}
          />
        </Box>
      </Collapse>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "grid",
          gridTemplateColumns: selected ? "minmax(0, 1fr) 300px" : "minmax(0, 1fr)",
          transition: "grid-template-columns 160ms ease",
        }}
      >
        <Box sx={{ minWidth: 0, minHeight: 0, position: "relative", display: "flex", flexDirection: "column" }}>
          {focus.focused && !replayData ? <BrainFocusBanner node={focus.focused} depth={focus.depth} setDepth={focus.setDepth} onClear={focus.clearFocus} /> : null}
          <Box sx={{ flex: 1, minHeight: 0 }}>
            <BrainGraphCanvas
              filters={filters.filters}
              onNodeSelect={setSelected}
              onNodeFocus={(node) => {
                focus.focusNode(node);
                setSelected(node);
              }}
              highlightedIds={highlightedIds}
              focusedIds={replayData ? undefined : focus.focusedIds}
              activeIds={replayData ? replay.activeNodeIds : activation.activeNodeIds}
              healthOverlay={healthOverlay}
              onHealthOverlayChange={setHealthOverlay}
              replayActiveIds={replayData ? replay.activeNodeIds : undefined}
              replaySessionNodeId={replaySessionNodeId}
              replayFocusedIds={replayData ? replayFocusedIds : undefined}
              pathEdgeIds={replayData ? pathEdgeIds : undefined}
              replayPlaying={replay.playing}
              onReplayNodeSelect={replayData ? handleReplayNodeSelect : undefined}
              showExport={!replayData}
              onShareOpen={() => setShareOpen(true)}
            />
          </Box>
        </Box>
        <NodeContentPanel node={selected} onClose={() => setSelected(null)} onNavigateTo={navigateToNode} />
      </Box>

      {replayData ? (
        <BrainReplayTransport data={replayData} controls={replay} onClose={closeReplay} />
      ) : (
        <>
          <Stack direction="row" alignItems="center" sx={{ borderTop: 1, borderColor: "divider", minHeight: 28, px: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
              Activity{liveSessionId ? ` · ${liveSessionId}` : ""}
              {activation.recentActivations.length ? ` · ${activation.recentActivations.length}` : ""}
            </Typography>
            <IconButton size="small" aria-label="Toggle activity" onClick={() => setActivityOpen((open) => !open)}>
              {activityOpen ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          </Stack>
          <Collapse in={activityOpen} unmountOnExit>
            <BrainActivationTimeline
              sessionId={liveSessionId || null}
              events={activation.recentActivations}
              paused={activation.paused}
              onPause={activation.setPaused}
              onClear={activation.clearActivations}
            />
          </Collapse>
        </>
      )}
      <BrainShareModal open={shareOpen} onClose={() => setShareOpen(false)} />
    </Box>
  );
}

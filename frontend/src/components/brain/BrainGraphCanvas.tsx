"use client";

import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import RefreshIcon from "@mui/icons-material/Refresh";
import { alpha, useTheme } from "@mui/material/styles";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import * as React from "react";
import type { Viewport } from "@xyflow/react";
import GraphEmptyState from "@/components/brain/GraphEmptyState";
import GraphLoadingOverlay from "@/components/brain/GraphLoadingOverlay";
import BrainHealthOverlay from "@/components/brain/BrainHealthOverlay";
import BrainExportMenu from "@/components/brain/BrainExportMenu";
import { nodeKindMeta } from "@/components/brain/nodes/node-kinds";
import { kindTitle } from "@/components/brain/brain-surface";
import { nodeKey } from "@/components/brain/graph-transform";
import { useBrainGraph } from "@/hooks/useBrainGraph";
import { useBrainHealth } from "@/hooks/useBrainHealth";
import { healthFlagsFromReport } from "@/types/brain-health";
import type { BrainGraphData, BrainGraphFilters, BrainNodeKind, GraphEdge, GraphNode } from "@/types/brain-graph";

type SimNode = SimulationNodeDatum & {
  id: string;
  key: string;
  kind: BrainNodeKind;
  label: string;
  summary: string;
  graphNode: GraphNode;
  degree: number;
  radius: number;
  color: string;
};

type SimLink = SimulationLinkDatum<SimNode> & {
  id: string;
  source: string | SimNode;
  target: string | SimNode;
};

type Props = {
  filters: BrainGraphFilters;
  onNodeSelect: (node: GraphNode) => void;
  onNodeFocus?: (node: GraphNode) => void;
  highlightedIds?: Set<string>;
  focusedIds?: Set<string>;
  activeIds?: Set<string>;
  workspaceId?: string;
  healthOverlay?: boolean;
  onHealthOverlayChange?: (enabled: boolean) => void;
  replayActiveIds?: Set<string>;
  replaySessionNodeId?: string | null;
  replayFocusedIds?: Set<string>;
  pathEdgeIds?: Set<string>;
  replayPlaying?: boolean;
  onReplayNodeSelect?: (node: GraphNode) => void;
  readOnly?: boolean;
  staticGraph?: BrainGraphData | null;
  staticLoading?: boolean;
  showExport?: boolean;
  onShareOpen?: () => void;
};

function edgeEndpointKey(kind: string, id: string): string {
  return nodeKey(kind, id);
}

function lightenHex(hex: string, amount = 0.28): string {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return hex;
  const r = Number.parseInt(raw.slice(0, 2), 16);
  const g = Number.parseInt(raw.slice(2, 4), 16);
  const b = Number.parseInt(raw.slice(4, 6), 16);
  const lift = (channel: number) => Math.min(255, Math.round(channel + (255 - channel) * amount));
  return `rgb(${lift(r)}, ${lift(g)}, ${lift(b)})`;
}

function darkenHex(hex: string, amount = 0.22): string {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return hex;
  const r = Number.parseInt(raw.slice(0, 2), 16);
  const g = Number.parseInt(raw.slice(2, 4), 16);
  const b = Number.parseInt(raw.slice(4, 6), 16);
  const drop = (channel: number) => Math.max(0, Math.round(channel * (1 - amount)));
  return `rgb(${drop(r)}, ${drop(g)}, ${drop(b)})`;
}

function buildSim(
  nodes: GraphNode[],
  edges: GraphEdge[],
  dark: boolean,
): { nodes: SimNode[]; links: SimLink[] } {
  const degree = new Map<string, number>();
  for (const edge of edges) {
    const source = edgeEndpointKey(edge.source_kind, edge.source_id);
    const target = edgeEndpointKey(edge.target_kind, edge.target_id);
    degree.set(source, (degree.get(source) ?? 0) + 1);
    degree.set(target, (degree.get(target) ?? 0) + 1);
  }
  const maxDegree = Math.max(1, ...Array.from(degree.values()), 1);

  const simNodes: SimNode[] = nodes.map((node, index) => {
    const key = nodeKey(node.kind, node.id);
    const deg = degree.get(key) ?? 0;
    const base = nodeKindMeta[node.kind]?.color ?? "#8b9199";
    const radius = 3.6 + (deg / maxDegree) * 5.5;
    const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2;
    const fill = node.deleted
      ? dark
        ? "#c4c9d4"
        : "#6b7280"
      : dark
        ? lightenHex(base, 0.62)
        : darkenHex(base, 0.08);
    return {
      id: key,
      key,
      kind: node.kind,
      label: node.label || node.id,
      summary: node.summary || "",
      graphNode: node,
      degree: deg,
      radius,
      color: fill,
      x: Math.cos(angle) * (110 + index * 0.6),
      y: Math.sin(angle) * (110 + index * 0.6),
    };
  });

  const idSet = new Set(simNodes.map((node) => node.id));
  const links: SimLink[] = edges.flatMap((edge): SimLink[] => {
      const source = edgeEndpointKey(edge.source_kind, edge.source_id);
      const target = edgeEndpointKey(edge.target_kind, edge.target_id);
      if (!idSet.has(source) || !idSet.has(target)) return [];
      return [{ id: edge.edge_id, source, target }];
    });

  return { nodes: simNodes, links };
}

function BrainForceCanvas({
  nodes,
  edges,
  loading,
  onNodeSelect,
  onNodeFocus,
  highlightedIds,
  focusedIds,
  activeIds,
  healthOverlay,
  onHealthOverlayChange,
  replayActiveIds,
  replayFocusedIds,
  pathEdgeIds,
  onReplayNodeSelect,
  readOnly,
  showExport,
  onShareOpen,
  workspaceId,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  loading: boolean;
  onNodeSelect: (node: GraphNode) => void;
  onNodeFocus?: (node: GraphNode) => void;
  highlightedIds?: Set<string>;
  focusedIds?: Set<string>;
  activeIds?: Set<string>;
  healthOverlay: boolean;
  onHealthOverlayChange?: (enabled: boolean) => void;
  replayActiveIds?: Set<string>;
  replayFocusedIds?: Set<string>;
  pathEdgeIds?: Set<string>;
  onReplayNodeSelect?: (node: GraphNode) => void;
  readOnly?: boolean;
  showExport?: boolean;
  onShareOpen?: () => void;
  workspaceId: string;
}) {
  const theme = useTheme();
  const dark = theme.palette.mode === "dark";
  const wrapRef = React.useRef<HTMLDivElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const simRef = React.useRef<Simulation<SimNode, SimLink> | null>(null);
  const nodesRef = React.useRef<SimNode[]>([]);
  const linksRef = React.useRef<SimLink[]>([]);
  const transformRef = React.useRef({ x: 0, y: 0, k: 1 });
  const hoverRef = React.useRef<SimNode | null>(null);
  const dragRef = React.useRef<{
    mode: "pan" | "node";
    node?: SimNode;
    lastX: number;
    lastY: number;
    moved: boolean;
  } | null>(null);
  const lastTapRef = React.useRef<{ id: string; at: number } | null>(null);
  const [, bump] = React.useState(0);
  const health = useBrainHealth({ enabled: !readOnly && healthOverlay });
  const healthFlags = React.useMemo(() => healthFlagsFromReport(health.report), [health.report]);

  const voidBg = theme.palette.background.default;
  const edgeColor = alpha(theme.palette.text.primary, dark ? 0.55 : 0.45);
  const edgeHot = alpha(theme.palette.text.primary, dark ? 0.9 : 0.75);
  const labelColor = alpha(theme.palette.text.primary, dark ? 0.98 : 0.95);
  const nodeRing = alpha(theme.palette.text.primary, dark ? 0.75 : 0.4);

  const effectiveActive = replayActiveIds ?? activeIds;

  const fitToNodes = React.useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodesRef.current.length === 0) return;
    const rect = canvas.getBoundingClientRect();
    if (rect.width < 40 || rect.height < 40) return;
    let minX = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    for (const node of nodesRef.current) {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      minX = Math.min(minX, x - node.radius);
      maxX = Math.max(maxX, x + node.radius);
      minY = Math.min(minY, y - node.radius);
      maxY = Math.max(maxY, y + node.radius);
    }
    const spanX = Math.max(80, maxX - minX);
    const spanY = Math.max(80, maxY - minY);
    const pad = 72;
    const k = Math.min(3.2, Math.max(1.1, Math.min((rect.width - pad * 2) / spanX, (rect.height - pad * 2) / spanY)));
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    transformRef.current = { x: -k * cx, y: -k * cy, k };
  }, []);

  const restartSimulation = React.useCallback(() => {
    simRef.current?.stop();
    const built = buildSim(nodes, edges, dark);
    nodesRef.current = built.nodes;
    linksRef.current = built.links;
    let ticks = 0;

    const simulation = forceSimulation(built.nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(built.links)
          .id((node) => node.id)
          .distance(88)
          .strength(0.5),
      )
      .force("charge", forceManyBody().strength(-320).distanceMax(620))
      .force(
        "collide",
        forceCollide<SimNode>()
          .radius((node) => node.radius + 4)
          .strength(0.95),
      )
      .force("x", forceX(0).strength(0.02))
      .force("y", forceY(0).strength(0.02))
      .force("center", forceCenter(0, 0))
      .alpha(1)
      .alphaDecay(0.022)
      .velocityDecay(0.32);

    simRef.current = simulation;
    simulation.on("tick", () => {
      ticks += 1;
      if (ticks === 40 || ticks === 120) fitToNodes();
      bump((value) => value + 1);
    });
    fitToNodes();
    bump((value) => value + 1);
  }, [dark, edges, fitToNodes, nodes]);

  React.useEffect(() => {
    restartSimulation();
    return () => {
      simRef.current?.stop();
      simRef.current = null;
    };
  }, [restartSimulation]);

  React.useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;
    const resize = () => {
      const rect = wrap.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      bump((value) => value + 1);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(wrap);
    return () => observer.disconnect();
  }, []);

  const screenToWorld = React.useCallback((clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const { x, y, k } = transformRef.current;
    return {
      x: (clientX - rect.left - rect.width / 2 - x) / k,
      y: (clientY - rect.top - rect.height / 2 - y) / k,
    };
  }, []);

  const findNode = React.useCallback((worldX: number, worldY: number) => {
    let hit: SimNode | null = null;
    let best = Number.POSITIVE_INFINITY;
    for (const node of nodesRef.current) {
      const dist = Math.hypot((node.x ?? 0) - worldX, (node.y ?? 0) - worldY);
      const reach = Math.max(node.radius + 5, 11) / Math.max(transformRef.current.k, 0.4);
      if (dist <= reach && dist < best) {
        best = dist;
        hit = node;
      }
    }
    return hit;
  }, []);

  const neighborIds = (() => {
    const hover = hoverRef.current;
    if (!hover) return null;
    const ids = new Set<string>([hover.id]);
    for (const link of linksRef.current) {
      const source = typeof link.source === "string" ? link.source : link.source.id;
      const target = typeof link.target === "string" ? link.target : link.target.id;
      if (source === hover.id) ids.add(target);
      if (target === hover.id) ids.add(source);
    }
    return ids;
  })();

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = canvas.width / dpr;
    const height = canvas.height / dpr;
    const { x: tx, y: ty, k } = transformRef.current;
    const hover = hoverRef.current;
    const hot = neighborIds;
    const search = highlightedIds;
    const focus = focusedIds ?? replayFocusedIds;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = voidBg;
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.translate(width / 2 + tx, height / 2 + ty);
    ctx.scale(k, k);

    for (const link of linksRef.current) {
      const source = link.source as SimNode | string;
      const target = link.target as SimNode | string;
      if (typeof source === "string" || typeof target === "string") continue;
      const onPath = pathEdgeIds?.has(link.id);
      const linked = !hot || (hot.has(source.id) && hot.has(target.id));
      const inFocus = !focus || (focus.has(source.id) && focus.has(target.id));
      ctx.beginPath();
      ctx.moveTo(source.x ?? 0, source.y ?? 0);
      ctx.lineTo(target.x ?? 0, target.y ?? 0);
      ctx.strokeStyle = onPath ? theme.palette.warning.main : linked && hot ? edgeHot : edgeColor;
      ctx.globalAlpha = hot ? (linked ? 1 : 0.1) : focus ? (inFocus ? 0.85 : 0.08) : 1;
      ctx.lineWidth = (onPath ? 2.4 : linked && hot ? 2 : 1.7) / k;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    for (const node of nodesRef.current) {
      const active = !hot || hot.has(node.id);
      const inFocus = !focus || focus.has(node.id);
      const searched = search?.has(node.id);
      const lit = effectiveActive?.has(node.id);
      let fill = node.color;
      if (healthOverlay) {
        if (healthFlags.orphanIds.has(node.id)) fill = "#ef4444";
        else if (healthFlags.staleIds.has(node.id)) fill = "#94a3b8";
        else if (healthFlags.hubIds.has(node.id)) fill = "#f59e0b";
      }

      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, node.radius, 0, Math.PI * 2);
      ctx.shadowColor = fill;
      ctx.shadowBlur = (dark ? 14 : 6) / k;
      ctx.fillStyle = fill;
      ctx.globalAlpha = hot ? (active ? 1 : 0.18) : focus ? (inFocus ? 1 : 0.18) : search ? (searched ? 1 : 0.2) : 1;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.lineWidth = 1.25 / k;
      ctx.strokeStyle = lit ? "#ffffff" : nodeRing;
      ctx.globalAlpha = 1;
      ctx.stroke();

      if (hover?.id === node.id || searched) {
        ctx.strokeStyle = labelColor;
        ctx.lineWidth = 1.8 / k;
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;

    if (hover) {
      const line1 = hover.label;
      const line2 = kindTitle(hover.kind);
      const fontSize = 12 / Math.max(k, 0.7);
      ctx.font = `500 ${fontSize}px ui-sans-serif, system-ui, sans-serif`;
      const w1 = ctx.measureText(line1).width;
      ctx.font = `400 ${(fontSize * 0.85).toFixed(2)}px ui-sans-serif, system-ui, sans-serif`;
      const w2 = ctx.measureText(line2).width;
      const textWidth = Math.max(w1, w2);
      const padX = 7 / k;
      const padY = 5 / k;
      const px = (hover.x ?? 0) + hover.radius + 9 / k;
      const py = (hover.y ?? 0);
      const boxW = textWidth + padX * 2;
      const boxH = fontSize * 1.85 + padY * 2;
      const bx = px;
      const by = py - boxH / 2;
      const r = 4 / k;
      ctx.fillStyle = dark ? "rgba(18,18,22,0.9)" : "rgba(255,255,255,0.94)";
      ctx.strokeStyle = dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)";
      ctx.lineWidth = 1 / k;
      ctx.beginPath();
      ctx.moveTo(bx + r, by);
      ctx.arcTo(bx + boxW, by, bx + boxW, by + boxH, r);
      ctx.arcTo(bx + boxW, by + boxH, bx, by + boxH, r);
      ctx.arcTo(bx, by + boxH, bx, by, r);
      ctx.arcTo(bx, by, bx + boxW, by, r);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = labelColor;
      ctx.font = `500 ${fontSize}px ui-sans-serif, system-ui, sans-serif`;
      ctx.fillText(line1, bx + padX, by + padY + fontSize * 0.9);
      ctx.fillStyle = dark ? "rgba(180,180,190,0.9)" : "rgba(90,90,100,0.95)";
      ctx.font = `400 ${(fontSize * 0.85).toFixed(2)}px ui-sans-serif, system-ui, sans-serif`;
      ctx.fillText(line2, bx + padX, by + padY + fontSize * 1.75);
    }

    ctx.restore();
  });

  const onWheel = (event: React.WheelEvent) => {
    event.preventDefault();
    const { k } = transformRef.current;
    transformRef.current.k = Math.min(4.5, Math.max(0.18, k * (event.deltaY < 0 ? 1.08 : 0.92)));
    bump((value) => value + 1);
  };

  const onPointerDown = (event: React.PointerEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.setPointerCapture(event.pointerId);
    const world = screenToWorld(event.clientX, event.clientY);
    const node = findNode(world.x, world.y);
    if (node && !readOnly) {
      node.fx = node.x;
      node.fy = node.y;
      dragRef.current = { mode: "node", node, lastX: event.clientX, lastY: event.clientY, moved: false };
      simRef.current?.alphaTarget(0.22).restart();
    } else {
      dragRef.current = { mode: "pan", lastX: event.clientX, lastY: event.clientY, moved: false };
    }
  };

  const onPointerMove = (event: React.PointerEvent) => {
    const drag = dragRef.current;
    if (!drag) {
      const world = screenToWorld(event.clientX, event.clientY);
      const node = findNode(world.x, world.y);
      if (hoverRef.current?.id !== node?.id) {
        hoverRef.current = node;
        bump((value) => value + 1);
      }
      if (canvasRef.current) canvasRef.current.style.cursor = node ? "pointer" : "grab";
      return;
    }
    const dx = event.clientX - drag.lastX;
    const dy = event.clientY - drag.lastY;
    if (Math.hypot(dx, dy) > 2) drag.moved = true;
    drag.lastX = event.clientX;
    drag.lastY = event.clientY;
    if (drag.mode === "pan") {
      transformRef.current.x += dx;
      transformRef.current.y += dy;
      bump((value) => value + 1);
      return;
    }
    if (drag.node) {
      const world = screenToWorld(event.clientX, event.clientY);
      drag.node.fx = world.x;
      drag.node.fy = world.y;
      drag.node.x = world.x;
      drag.node.y = world.y;
      bump((value) => value + 1);
    }
  };

  const onPointerUp = () => {
    const drag = dragRef.current;
    dragRef.current = null;
    if (!drag) return;
    if (drag.mode === "node" && drag.node) {
      drag.node.fx = null;
      drag.node.fy = null;
      simRef.current?.alphaTarget(0).restart();
      if (!drag.moved) {
        const now = Date.now();
        const last = lastTapRef.current;
        if (last && last.id === drag.node.id && now - last.at < 320) {
          onNodeFocus?.(drag.node.graphNode);
          lastTapRef.current = null;
        } else {
          lastTapRef.current = { id: drag.node.id, at: now };
          if (onReplayNodeSelect && replayActiveIds?.has(drag.node.id)) {
            onReplayNodeSelect(drag.node.graphNode);
          } else {
            onNodeSelect(drag.node.graphNode);
          }
        }
      }
    }
  };

  const stubViewport = React.useCallback((): Viewport => ({ x: transformRef.current.x, y: transformRef.current.y, zoom: transformRef.current.k }), []);
  const stubSetViewport = React.useCallback((viewport: Viewport) => {
    transformRef.current = { x: viewport.x, y: viewport.y, k: viewport.zoom };
    bump((value) => value + 1);
  }, []);

  if (!loading && edges.length === 0) {
    return <GraphEmptyState />;
  }

  return (
    <Box
      ref={wrapRef}
      sx={{
        position: "relative",
        height: "100%",
        minHeight: 0,
        borderRadius: 2,
        border: 1,
        borderColor: "divider",
        overflow: "hidden",
        bgcolor: voidBg,
      }}
    >
      <canvas
        ref={canvasRef}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={() => {
          hoverRef.current = null;
          dragRef.current = null;
          bump((value) => value + 1);
        }}
        style={{ width: "100%", height: "100%", display: "block", touchAction: "none" }}
      />
      <Stack
        direction="row"
        spacing={0.75}
        alignItems="center"
        sx={{
          position: "absolute",
          top: 10,
          left: 10,
          right: 10,
          zIndex: 5,
          bgcolor: alpha(theme.palette.background.paper, 0.72),
          backdropFilter: "blur(10px)",
          border: 1,
          borderColor: "divider",
          borderRadius: 1.5,
          px: 1,
          py: 0.35,
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ flex: 1, minWidth: 0 }} noWrap>
          {hoverRef.current
            ? `${hoverRef.current.label} · ${kindTitle(hoverRef.current.kind)}`
            : `${nodes.length} nodes · ${edges.length} links · scroll zoom · drag to pan`}
        </Typography>
        {showExport ? (
          <BrainExportMenu
            canvasRef={wrapRef}
            fitView={() => {
              transformRef.current = { x: 0, y: 0, k: 1 };
              bump((value) => value + 1);
            }}
            getViewport={stubViewport}
            setViewport={stubSetViewport}
            workspaceId={workspaceId}
            onShare={onShareOpen}
          />
        ) : null}
        {onHealthOverlayChange && !readOnly ? (
          <BrainHealthOverlay enabled={healthOverlay} onChange={onHealthOverlayChange} />
        ) : null}
        <IconButton
          size="small"
          aria-label="Reheat layout"
          onClick={() => {
            restartSimulation();
          }}
        >
          <RefreshIcon fontSize="small" />
        </IconButton>
      </Stack>
      {loading ? <GraphLoadingOverlay /> : null}
    </Box>
  );
}

export default function BrainGraphCanvas(props: Props) {
  const fetched = useBrainGraph(props.filters, { enabled: !props.staticGraph });
  const nodes = props.staticGraph?.nodes ?? fetched.nodes;
  const edges = props.staticGraph?.edges ?? fetched.edges;
  const loading = props.staticGraph ? Boolean(props.staticLoading) : fetched.loading;

  return (
    <BrainForceCanvas
      nodes={nodes}
      edges={edges}
      loading={loading}
      onNodeSelect={props.onNodeSelect}
      onNodeFocus={props.onNodeFocus}
      highlightedIds={props.highlightedIds}
      focusedIds={props.focusedIds}
      activeIds={props.activeIds}
      healthOverlay={Boolean(props.healthOverlay)}
      onHealthOverlayChange={props.onHealthOverlayChange}
      replayActiveIds={props.replayActiveIds}
      replayFocusedIds={props.replayFocusedIds}
      pathEdgeIds={props.pathEdgeIds}
      onReplayNodeSelect={props.onReplayNodeSelect}
      readOnly={props.readOnly}
      showExport={props.showExport}
      onShareOpen={props.onShareOpen}
      workspaceId={props.workspaceId ?? "default"}
    />
  );
}

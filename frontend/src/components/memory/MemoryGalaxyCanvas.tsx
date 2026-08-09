"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
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
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import { ceApi } from "@/lib/ce-api";

export type VaultGraphPayload = {
  nodes: Array<{ id: string; label: string }>;
  edges: Array<{ source: string; target: string }>;
};

/** Kept for page compat; Galaxy is always a live force canvas now. */
export type GalaxyLayoutMode = "circle" | "force";

type SimNode = SimulationNodeDatum & {
  id: string;
  label: string;
  degree: number;
  radius: number;
  color: string;
};

type SimLink = SimulationLinkDatum<SimNode> & {
  source: string | SimNode;
  target: string | SimNode;
};

type Props = {
  graph?: VaultGraphPayload;
  loading?: boolean;
  layoutMode?: GalaxyLayoutMode;
  onLayoutModeChange?: (mode: GalaxyLayoutMode) => void;
};

function hashHue(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  return hash % 360;
}

function degreeMap(edges: VaultGraphPayload["edges"]): Map<string, number> {
  const map = new Map<string, number>();
  for (const edge of edges) {
    map.set(edge.source, (map.get(edge.source) ?? 0) + 1);
    map.set(edge.target, (map.get(edge.target) ?? 0) + 1);
  }
  return map;
}

function buildSimGraph(payload: VaultGraphPayload, dark: boolean): { nodes: SimNode[]; links: SimLink[] } {
  const degrees = degreeMap(payload.edges);
  const maxDegree = Math.max(1, ...Array.from(degrees.values()), 1);
  const nodes: SimNode[] = payload.nodes.map((node, index) => {
    const degree = degrees.get(node.id) ?? 0;
    const hue = hashHue(node.id);
    const color = dark
      ? `hsl(${hue} 55% ${degree === 0 ? 62 : 72}%)`
      : `hsl(${hue} 48% ${degree === 0 ? 48 : 42}%)`;
    const angle = (index / Math.max(1, payload.nodes.length)) * Math.PI * 2;
    return {
      id: node.id,
      label: node.label || node.id,
      degree,
      radius: 4.2 + (degree / maxDegree) * 8,
      color,
      x: Math.cos(angle) * (80 + index),
      y: Math.sin(angle) * (80 + index),
    };
  });
  const idSet = new Set(nodes.map((node) => node.id));
  const links: SimLink[] = payload.edges
    .filter((edge) => idSet.has(edge.source) && idSet.has(edge.target))
    .map((edge) => ({ source: edge.source, target: edge.target }));
  return { nodes, links };
}

function GalaxyCanvas({
  payload,
  onOpenNote,
}: {
  payload: VaultGraphPayload;
  onOpenNote: (path: string) => void;
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
  const [, bump] = React.useState(0);

  const voidBg = "var(--kp-bg)";
  const edgeColor = alpha(theme.palette.text.primary, dark ? 0.45 : 0.28);
  const edgeHot = alpha(theme.palette.text.primary, dark ? 0.88 : 0.65);
  const labelColor = alpha(theme.palette.text.primary, dark ? 0.96 : 0.9);

  const restartSimulation = React.useCallback(() => {
    simRef.current?.stop();
    const built = buildSimGraph(payload, dark);
    nodesRef.current = built.nodes;
    linksRef.current = built.links;

    const simulation = forceSimulation(built.nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(built.links)
          .id((node) => node.id)
          .distance(56)
          .strength(0.45),
      )
      .force("charge", forceManyBody().strength(-180).distanceMax(420))
      .force(
        "collide",
        forceCollide<SimNode>()
          .radius((node) => node.radius + 3)
          .strength(0.9),
      )
      .force("x", forceX(0).strength(0.035))
      .force("y", forceY(0).strength(0.035))
      .force("center", forceCenter(0, 0))
      .alpha(1)
      .alphaDecay(0.028)
      .velocityDecay(0.35);

    simRef.current = simulation;
    simulation.on("tick", () => bump((value) => value + 1));
    bump((value) => value + 1);
  }, [dark, payload]);

  React.useEffect(() => {
    restartSimulation();
    return () => {
      simRef.current?.stop();
      simRef.current = null;
    };
  }, [restartSimulation]);

  const screenToWorld = React.useCallback((clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const { x, y, k } = transformRef.current;
    // Match canvas draw: translate(width/2 + tx, height/2 + ty) then scale(k).
    return {
      x: (clientX - rect.left - rect.width / 2 - x) / k,
      y: (clientY - rect.top - rect.height / 2 - y) / k,
    };
  }, []);

  const findNode = React.useCallback((worldX: number, worldY: number) => {
    let hit: SimNode | null = null;
    let best = Number.POSITIVE_INFINITY;
    const hitPad = 14 / Math.max(transformRef.current.k, 0.4);
    for (const node of nodesRef.current) {
      const dx = (node.x ?? 0) - worldX;
      const dy = (node.y ?? 0) - worldY;
      const dist = Math.hypot(dx, dy);
      const reach = node.radius + hitPad;
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
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

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

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = voidBg;
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.translate(width / 2 + tx, height / 2 + ty);
    ctx.scale(k, k);

    // Edges
    for (const link of linksRef.current) {
      const source = link.source as SimNode | string;
      const target = link.target as SimNode | string;
      if (typeof source === "string" || typeof target === "string") continue;
      const linked = !hot || (hot.has(source.id) && hot.has(target.id));
      ctx.beginPath();
      ctx.moveTo(source.x ?? 0, source.y ?? 0);
      ctx.lineTo(target.x ?? 0, target.y ?? 0);
      ctx.strokeStyle = linked && hot ? edgeHot : edgeColor;
      ctx.globalAlpha = hot ? (linked ? 0.9 : 0.08) : 1;
      ctx.lineWidth = linked && hot ? 1.25 / k : 1 / k;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Nodes
    for (const node of nodesRef.current) {
      const active = !hot || hot.has(node.id);
      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, node.radius, 0, Math.PI * 2);
      if (dark) {
        ctx.shadowColor = node.color;
        ctx.shadowBlur = 10 / k;
      }
      ctx.fillStyle = node.color;
      ctx.globalAlpha = active ? 1 : 0.14;
      ctx.fill();
      ctx.shadowBlur = 0;
      if (hover && hover.id === node.id) {
        ctx.strokeStyle = labelColor;
        ctx.lineWidth = 1.5 / k;
        ctx.globalAlpha = 1;
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;

    // Hover label (Obsidian-style floating title)
    if (hover) {
      const label = hover.label;
      const fontSize = 12 / Math.max(k, 0.65);
      ctx.font = `500 ${fontSize}px ui-sans-serif, system-ui, sans-serif`;
      const textWidth = ctx.measureText(label).width;
      const px = (hover.x ?? 0) + hover.radius + 8 / k;
      const py = (hover.y ?? 0) - 4 / k;
      const padX = 6 / k;
      const padY = 4 / k;
      ctx.fillStyle = dark ? "rgba(20,20,24,0.88)" : "rgba(255,255,255,0.92)";
      ctx.strokeStyle = dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)";
      ctx.lineWidth = 1 / k;
      const boxW = textWidth + padX * 2;
      const boxH = fontSize + padY * 2;
      ctx.beginPath();
      const r = 4 / k;
      const bx = px;
      const by = py - boxH;
      ctx.moveTo(bx + r, by);
      ctx.arcTo(bx + boxW, by, bx + boxW, by + boxH, r);
      ctx.arcTo(bx + boxW, by + boxH, bx, by + boxH, r);
      ctx.arcTo(bx, by + boxH, bx, by, r);
      ctx.arcTo(bx, by, bx + boxW, by, r);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = labelColor;
      ctx.fillText(label, px + padX, py - padY - 2 / k);
    }

    ctx.restore();
  });

  const onWheel = (event: React.WheelEvent) => {
    event.preventDefault();
    const { k } = transformRef.current;
    const next = Math.min(4, Math.max(0.2, k * (event.deltaY < 0 ? 1.08 : 0.92)));
    transformRef.current.k = next;
    bump((value) => value + 1);
  };

  const onPointerDown = (event: React.PointerEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.setPointerCapture(event.pointerId);
    const world = screenToWorld(event.clientX, event.clientY);
    const node = findNode(world.x, world.y);
    if (node) {
      node.fx = node.x;
      node.fy = node.y;
      dragRef.current = { mode: "node", node, lastX: event.clientX, lastY: event.clientY, moved: false };
      simRef.current?.alphaTarget(0.25).restart();
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
    if (Math.hypot(dx, dy) > 4) drag.moved = true;
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

  const onPointerUp = (event: React.PointerEvent) => {
    const drag = dragRef.current;
    dragRef.current = null;
    if (!drag) return;

    if (drag.mode === "node" && drag.node) {
      drag.node.fx = null;
      drag.node.fy = null;
      simRef.current?.alphaTarget(0).restart();
      if (!drag.moved) onOpenNote(drag.node.id);
    }
  };

  return (
    <Box ref={wrapRef} sx={{ position: "relative", width: "100%", height: "100%", bgcolor: voidBg }}>
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
        spacing={0.5}
        alignItems="center"
        sx={{
          position: "absolute",
          top: 12,
          right: 12,
          bgcolor: alpha(theme.palette.background.paper, 0.72),
          backdropFilter: "blur(8px)",
          border: 1,
          borderColor: "divider",
          borderRadius: 1.5,
          px: 0.5,
          py: 0.25,
        }}
      >
            <Typography variant="caption" color="text.secondary" sx={{ px: 1 }}>
              {hoverRef.current?.label || `${payload.nodes.length} notes · ${payload.edges.length} links · click a note to read`}
            </Typography>
        <IconButton
          size="small"
          aria-label="Reheat force layout"
          onClick={() => {
            transformRef.current = { x: 0, y: 0, k: 1 };
            restartSimulation();
          }}
        >
          <RefreshIcon fontSize="small" />
        </IconButton>
      </Stack>
    </Box>
  );
}

function GalaxyInner({ graph, loading }: Props) {
  const [selectedPath, setSelectedPath] = React.useState<string | null>(null);
  const [noteContent, setNoteContent] = React.useState<string | null>(null);
  const [noteError, setNoteError] = React.useState<string | null>(null);
  const [noteLoading, setNoteLoading] = React.useState(false);

  const openNote = React.useCallback(async (path: string) => {
    setSelectedPath(path);
    setNoteContent(null);
    setNoteError(null);
    setNoteLoading(true);
    try {
      const encoded = path
        .split("/")
        .map((segment) => encodeURIComponent(segment))
        .join("/");
      const response = await ceApi(`/api/vault/files/${encoded}`);
      if (!response.ok) {
        throw new Error((await response.text()) || "Note not found in vault");
      }
      const payload = (await response.json()) as { content?: string };
      setNoteContent(payload.content ?? "(empty note)");
    } catch (err) {
      setNoteError(err instanceof Error ? err.message : "Could not open note");
    } finally {
      setNoteLoading(false);
    }
  }, []);

  if (loading) {
    return (
      <Box sx={{ height: "100%", display: "grid", placeItems: "center", bgcolor: "background.default" }}>
        <Typography color="text.secondary" variant="body2">
          Loading vault graph…
        </Typography>
      </Box>
    );
  }

  const payload = graph ?? { nodes: [], edges: [] };
  if (!payload.nodes.length) {
    return (
      <EmptyState
        title="Your vault is empty"
        description="Connect a markdown vault, then capture notes from chat or Agent OS memory workflows."
        actionLabel="Vault settings"
        onAction={() => {
          window.location.href = "/settings/vault";
        }}
      />
    );
  }

  return (
    <>
      <GalaxyCanvas payload={payload} onOpenNote={(path) => void openNote(path)} />
      <Drawer
        anchor="right"
        open={Boolean(selectedPath)}
        onClose={() => setSelectedPath(null)}
        PaperProps={{ sx: { width: { xs: "100%", sm: 420 }, p: 2.5 } }}
      >
        <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
          {selectedPath || "Note"}
        </Typography>
        {noteLoading ? (
          <Typography color="text.secondary" variant="body2">
            Loading…
          </Typography>
        ) : null}
        {noteError ? (
          <ErrorState title="Could not open note" message={noteError} onRetry={() => selectedPath && void openNote(selectedPath)} />
        ) : null}
        {noteContent ? (
          <Box
            component="pre"
            sx={{
              m: 0,
              whiteSpace: "pre-wrap",
              fontSize: "0.85rem",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          >
            {noteContent}
          </Box>
        ) : null}
        <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
          <Button component="a" href="/settings/vault" size="small" variant="outlined" sx={{ textTransform: "none" }}>
            Vault settings
          </Button>
          <Button size="small" onClick={() => setSelectedPath(null)} sx={{ textTransform: "none" }}>
            Close
          </Button>
        </Stack>
      </Drawer>
    </>
  );
}

export default function MemoryGalaxyCanvas(props: Props) {
  return (
    <Box
      sx={{
        height: "100%",
        minHeight: 560,
        borderRadius: 2,
        overflow: "hidden",
        border: 1,
        borderColor: "divider",
      }}
    >
      <GalaxyInner {...props} />
    </Box>
  );
}

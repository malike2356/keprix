"use client";

import Box from "@mui/material/Box";
import { useReactFlow, type Node, type XYPosition } from "@xyflow/react";
import * as React from "react";
import type { ClusterGroup } from "@/components/brain/clustering";
import { nodeKindColor } from "@/components/brain/nodes/node-kinds";
import type { BrainFlowNodeData } from "@/types/brain-graph";

type Props = {
  nodes: Node<BrainFlowNodeData>[];
  clusters: ClusterGroup[];
  showClusters: boolean;
  width?: number;
  height?: number;
};

function boundsOfNodes(nodes: Node<BrainFlowNodeData>[]) {
  if (nodes.length === 0) {
    return { minX: -100, minY: -100, maxX: 100, maxY: 100 };
  }
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const node of nodes) {
    const radius = (node.data.size ?? 44) / 2;
    minX = Math.min(minX, node.position.x - radius);
    minY = Math.min(minY, node.position.y - radius);
    maxX = Math.max(maxX, node.position.x + radius);
    maxY = Math.max(maxY, node.position.y + radius);
  }
  return { minX, minY, maxX, maxY };
}

function project(
  position: XYPosition,
  bounds: ReturnType<typeof boundsOfNodes>,
  width: number,
  height: number,
): XYPosition {
  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const scale = Math.min(width / spanX, height / spanY);
  return {
    x: (position.x - bounds.minX) * scale,
    y: (position.y - bounds.minY) * scale,
  };
}

export default function BrainMinimap({
  nodes,
  clusters,
  showClusters,
  width = 180,
  height = 120,
}: Props) {
  const { getViewport, setViewport } = useReactFlow();
  const bounds = React.useMemo(() => boundsOfNodes(nodes), [nodes]);
  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const scale = Math.min(width / spanX, height / spanY);

  const viewportRect = React.useMemo(() => {
    const viewport = getViewport();
    const worldWidth = width / viewport.zoom;
    const worldHeight = height / viewport.zoom;
    const topLeft = {
      x: (-viewport.x) / viewport.zoom,
      y: (-viewport.y) / viewport.zoom,
    };
    return {
      x: (topLeft.x - bounds.minX) * scale,
      y: (topLeft.y - bounds.minY) * scale,
      width: worldWidth * scale,
      height: worldHeight * scale,
    };
  }, [bounds.minX, bounds.minY, getViewport, height, scale, width]);

  const handleClick = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    const worldX = clickX / scale + bounds.minX;
    const worldY = clickY / scale + bounds.minY;
    const viewport = getViewport();
    setViewport({
      x: -worldX * viewport.zoom + width / 2,
      y: -worldY * viewport.zoom + height / 2,
      zoom: viewport.zoom,
    });
  };

  return (
    <Box
      sx={{
        position: "absolute",
        right: 12,
        bottom: 12,
        width,
        height,
        borderRadius: 1.5,
        border: 1,
        borderColor: "divider",
        bgcolor: (theme) => theme.palette.background.paper,
        opacity: 0.94,
        overflow: "hidden",
        zIndex: 4,
      }}
    >
      <svg width={width} height={height} onClick={handleClick} style={{ cursor: "pointer" }}>
        {showClusters
          ? clusters.map((cluster) => {
              const topLeft = project(
                { x: cluster.bounds.x, y: cluster.bounds.y },
                bounds,
                width,
                height,
              );
              return (
                <rect
                  key={cluster.id}
                  x={topLeft.x}
                  y={topLeft.y}
                  width={cluster.bounds.width * scale}
                  height={cluster.bounds.height * scale}
                  fill={`${nodeKindColor({ data: { kind: cluster.dominantKind } })}22`}
                  stroke="none"
                />
              );
            })
          : null}
        {nodes.map((node) => {
          const point = project(node.position, bounds, width, height);
          return (
            <circle
              key={node.id}
              cx={point.x}
              cy={point.y}
              r={3}
              fill={nodeKindColor(node)}
            />
          );
        })}
        <rect
          x={viewportRect.x}
          y={viewportRect.y}
          width={viewportRect.width}
          height={viewportRect.height}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={1.5}
        />
      </svg>
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import * as React from "react";
import AgentTaskNode from "@/components/playbooks/studio/nodes/AgentTaskNode";
import ArtifactNode from "@/components/playbooks/studio/nodes/ArtifactNode";
import ConditionNode from "@/components/playbooks/studio/nodes/ConditionNode";
import DelayNode from "@/components/playbooks/studio/nodes/DelayNode";
import HumanApprovalNode from "@/components/playbooks/studio/nodes/HumanApprovalNode";
import HttpNode from "@/components/playbooks/studio/nodes/HttpNode";
import ParallelNode from "@/components/playbooks/studio/nodes/ParallelNode";
import TriggerNode from "@/components/playbooks/studio/nodes/TriggerNode";
import type { StudioEdge, StudioNode, StudioNodeType } from "@/lib/playbook-studio/canvas-types";
import { nodeDefinition } from "@/lib/playbook-studio/node-registry";

const nodeTypes = {
  trigger: TriggerNode,
  agent_task: AgentTaskNode,
  http: HttpNode,
  condition: ConditionNode,
  human_approval: HumanApprovalNode,
  parallel: ParallelNode,
  artifact: ArtifactNode,
  delay: DelayNode,
};

type Props = {
  nodes: StudioNode[];
  edges: StudioEdge[];
  selectedNodeId: string | null;
  invalidNodeIds: Set<string>;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onNodesUpdate: (nodes: StudioNode[]) => void;
  onEdgesUpdate: (edges: StudioEdge[]) => void;
  onSelectNode: (nodeId: string | null) => void;
  readOnly?: boolean;
};

export default function PlaybookCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <PlaybookCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

function PlaybookCanvasInner({
  nodes,
  edges,
  selectedNodeId,
  invalidNodeIds,
  onNodesChange,
  onEdgesChange,
  onNodesUpdate,
  onEdgesUpdate,
  onSelectNode,
  readOnly,
}: Props) {
  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const { screenToFlowPosition } = useReactFlow();
  const flowNodes = React.useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        selected: node.id === selectedNodeId,
        data: { ...node.data, invalid: invalidNodeIds.has(node.id) },
      })) as Node[],
    [invalidNodeIds, nodes, selectedNodeId],
  );
  const flowEdges = React.useMemo(() => edges as Edge[], [edges]);

  const onConnect = React.useCallback<OnConnect>(
    (connection: Connection) => {
      const when = connection.sourceHandle === "true" || connection.sourceHandle === "false"
        ? connection.sourceHandle
        : null;
      const edge = {
        ...connection,
        id: `e_${connection.source}_${connection.target}_${when || "next"}`,
        data: { when },
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
      } as Edge;
      onEdgesUpdate(addEdge(edge, edges as Edge[]) as StudioEdge[]);
    },
    [edges, onEdgesUpdate],
  );

  const onDragOver = React.useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = React.useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const raw = event.dataTransfer.getData("application/reactflow");
      if (!raw) return;
      const type = raw as StudioNodeType;
      const definition = nodeDefinition(type);
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      const count = nodes.filter((node) => node.type === type).length + 1;
      const id = type === "trigger" ? "trigger" : `${type}_${count}`;
      if (nodes.some((node) => node.id === id)) return;
      onNodesUpdate([
        ...nodes,
        {
          id,
          type,
          position,
          data: { ...definition.defaults },
        },
      ]);
      onSelectNode(id);
    },
    [nodes, onNodesUpdate, onSelectNode, screenToFlowPosition],
  );

  return (
    <Box ref={wrapperRef} sx={{ height: "100%", minHeight: 560 }}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        snapToGrid
        snapGrid={[20, 20]}
        fitView
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDragOver={readOnly ? undefined : onDragOver}
        onDrop={readOnly ? undefined : onDrop}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        onNodeClick={(_, node) => onSelectNode(node.id)}
        onPaneClick={() => onSelectNode(null)}
      >
        <Background gap={20} />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </Box>
  );
}

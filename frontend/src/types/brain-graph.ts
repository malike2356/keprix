export type BrainNodeKind = "memory" | "skill" | "task" | "tool" | "session" | "document" | "source" | "entity";

export type GraphNode = {
  id: string;
  kind: BrainNodeKind;
  label: string;
  summary: string;
  created_at: string;
  updated_at?: string | null;
  metadata: Record<string, unknown>;
  deleted: boolean;
  content?: Record<string, unknown>;
};

export type GraphEdge = {
  edge_id: string;
  source_kind: BrainNodeKind;
  source_id: string;
  target_kind: BrainNodeKind;
  target_id: string;
  relation: string;
  weight: number;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type BrainGraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  truncated: boolean;
};

export type BrainGraphFilters = {
  kinds?: BrainNodeKind[];
  sessionId?: string;
  since?: string;
  limit?: number;
};

export type BrainFlowNodeData = GraphNode & {
  degree: number;
  size: number;
  dimmed?: boolean;
  highlighted?: boolean;
  active?: boolean;
  healthOrphan?: boolean;
  healthStale?: boolean;
  healthHub?: boolean;
  healthDuplicate?: boolean;
};

export type BrainActivationEvent = {
  type: string;
  workspace_id: string;
  session_id: string;
  node_kind: BrainNodeKind;
  node_id: string;
  relation?: string | null;
  confidence?: number | null;
  ts: string;
};

export type StudioNodeType =
  | "trigger"
  | "agent_task"
  | "http"
  | "condition"
  | "human_approval"
  | "parallel"
  | "artifact"
  | "delay";

export type StudioVariable = {
  name: string;
  type: "string" | "number" | "boolean";
  default?: string | number | boolean;
  description?: string;
};

export type StudioPosition = { x: number; y: number };

export type StudioNodeData = {
  label?: string;
  description?: string;
  prompt?: string;
  tools?: string[];
  connector_id?: string | null;
  url?: string;
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  expression?: string;
  trueLabel?: string;
  falseLabel?: string;
  message?: string;
  risk?: "low" | "medium" | "high";
  summary?: string;
  tasks?: Array<Record<string, unknown>>;
  name?: string;
  content?: string;
  from_key?: string;
  runStatus?: "pending" | "running" | "completed" | "failed" | "skipped" | "waiting_approval";
};

export type StudioNode = {
  id: string;
  type: StudioNodeType;
  position: StudioPosition;
  data: StudioNodeData;
};

export type StudioEdge = {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
  data?: { when?: string | null };
};

export type StudioCanvas = {
  schema_version: 1;
  id: string;
  name: string;
  description?: string;
  entry?: string | null;
  nodes: StudioNode[];
  edges: StudioEdge[];
  viewport?: { x: number; y: number; zoom: number };
  variables?: StudioVariable[];
};

export type StudioCompileError = {
  code: string;
  message: string;
  severity?: "error" | "warning";
  node_id?: string;
};

export type StudioPlaybookSummary = {
  id: string;
  name: string;
  updated_at: number;
};

export type StudioLoadResponse = {
  yaml: Record<string, unknown>;
  layout: Record<string, unknown> | null;
  canvas: StudioCanvas;
};

export const DEFAULT_STUDIO_CANVAS: StudioCanvas = {
  schema_version: 1,
  id: "new_playbook",
  name: "New playbook",
  description: "",
  entry: "trigger",
  nodes: [
    {
      id: "trigger",
      type: "trigger",
      position: { x: 80, y: 140 },
      data: { label: "Trigger" },
    },
    {
      id: "agent_task_1",
      type: "agent_task",
      position: { x: 360, y: 140 },
      data: { label: "Agent task", prompt: "Describe the task", tools: [] },
    },
  ],
  edges: [
    {
      id: "e_trigger_agent_task_1",
      source: "trigger",
      target: "agent_task_1",
      sourceHandle: null,
      targetHandle: null,
      data: { when: null },
    },
  ],
  viewport: { x: 0, y: 0, zoom: 1 },
};

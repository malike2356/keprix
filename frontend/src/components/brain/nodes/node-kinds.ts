import ArticleIcon from "@mui/icons-material/Article";
import BoltIcon from "@mui/icons-material/Bolt";
import BuildIcon from "@mui/icons-material/Build";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import CheckIcon from "@mui/icons-material/Check";
import HubIcon from "@mui/icons-material/Hub";
import LinkIcon from "@mui/icons-material/Link";
import PsychologyIcon from "@mui/icons-material/Psychology";
import type { ComponentType } from "react";
import type { NodeProps } from "@xyflow/react";
import type { BrainFlowNodeData, BrainNodeKind } from "@/types/brain-graph";
import MemoryNode from "@/components/brain/nodes/MemoryNode";
import SkillNode from "@/components/brain/nodes/SkillNode";
import TaskNode from "@/components/brain/nodes/TaskNode";
import ToolNode from "@/components/brain/nodes/ToolNode";
import SessionNode from "@/components/brain/nodes/SessionNode";
import DocumentNode from "@/components/brain/nodes/DocumentNode";
import SourceNode from "@/components/brain/nodes/SourceNode";
import DeletedNode from "@/components/brain/nodes/DeletedNode";
import ClusterBubble from "@/components/brain/ClusterBubble";

/** Restrained palette aligned with Keprix semantics (NotebookLM-calm, still kind-distinct). */
export const nodeKindMeta: Record<BrainNodeKind, { color: string; shape: "circle" | "diamond" | "square" | "hexagon" | "rounded" | "folded"; Icon: typeof PsychologyIcon }> = {
  memory: { color: "#6495ed", shape: "circle", Icon: PsychologyIcon },
  skill: { color: "#c4a35a", shape: "diamond", Icon: BoltIcon },
  task: { color: "#3d9b7a", shape: "square", Icon: CheckIcon },
  tool: { color: "#8b9199", shape: "hexagon", Icon: BuildIcon },
  session: { color: "#8b7cf0", shape: "rounded", Icon: ChatBubbleOutlineIcon },
  document: { color: "#c47b4a", shape: "folded", Icon: ArticleIcon },
  source: { color: "#b86b7a", shape: "circle", Icon: LinkIcon },
  entity: { color: "#3d9b90", shape: "hexagon", Icon: HubIcon },
};

export const NODE_TYPES: Record<string, ComponentType<NodeProps>> = {
  cluster: ClusterBubble as ComponentType<NodeProps>,
  memory: MemoryNode as ComponentType<NodeProps>,
  skill: SkillNode as ComponentType<NodeProps>,
  task: TaskNode as ComponentType<NodeProps>,
  tool: ToolNode as ComponentType<NodeProps>,
  session: SessionNode as ComponentType<NodeProps>,
  document: DocumentNode as ComponentType<NodeProps>,
  source: SourceNode as ComponentType<NodeProps>,
  entity: MemoryNode as ComponentType<NodeProps>,
  deleted: DeletedNode as ComponentType<NodeProps>,
};

export function nodeKindColor(node: { type?: string; data?: Partial<BrainFlowNodeData> }): string {
  if (node.data?.deleted || node.type === "deleted") return "#94a3b8";
  const kind = node.data?.kind;
  return kind ? nodeKindMeta[kind]?.color ?? "#64748b" : "#64748b";
}

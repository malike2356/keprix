import type { NodeProps } from "@xyflow/react";
import BrainNodeBase from "@/components/brain/nodes/BrainNodeBase";

export default function ToolNode(props: NodeProps) {
  return <BrainNodeBase {...props} kind="tool" />;
}

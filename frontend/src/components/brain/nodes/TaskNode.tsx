import type { NodeProps } from "@xyflow/react";
import BrainNodeBase from "@/components/brain/nodes/BrainNodeBase";

export default function TaskNode(props: NodeProps) {
  return <BrainNodeBase {...props} kind="task" />;
}

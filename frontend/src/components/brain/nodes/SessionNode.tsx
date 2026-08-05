import type { NodeProps } from "@xyflow/react";
import BrainNodeBase from "@/components/brain/nodes/BrainNodeBase";

export default function SessionNode(props: NodeProps) {
  return <BrainNodeBase {...props} kind="session" />;
}

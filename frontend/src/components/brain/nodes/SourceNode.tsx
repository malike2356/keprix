import type { NodeProps } from "@xyflow/react";
import BrainNodeBase from "@/components/brain/nodes/BrainNodeBase";

export default function SourceNode(props: NodeProps) {
  return <BrainNodeBase {...props} kind="source" />;
}

import type { NodeProps } from "@xyflow/react";
import BrainNodeBase from "@/components/brain/nodes/BrainNodeBase";

export default function DocumentNode(props: NodeProps) {
  return <BrainNodeBase {...props} kind="document" />;
}

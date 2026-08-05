import type { NodeProps } from "@xyflow/react";
import BrainNodeBase from "@/components/brain/nodes/BrainNodeBase";

export default function SkillNode(props: NodeProps) {
  return <BrainNodeBase {...props} kind="skill" />;
}

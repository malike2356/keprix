"use client";

import type { NodeProps } from "@xyflow/react";
import StudioNodeBase from "@/components/playbooks/studio/nodes/StudioNodeBase";
import type { StudioNodeData } from "@/lib/playbook-studio/canvas-types";

export default function ConditionNode(props: NodeProps) {
  return (
    <StudioNodeBase
      {...props}
      type="condition"
      data={props.data as StudioNodeData}
      conditionHandles
    />
  );
}

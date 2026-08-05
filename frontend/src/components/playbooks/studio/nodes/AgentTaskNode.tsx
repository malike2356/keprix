"use client";

import type { NodeProps } from "@xyflow/react";
import StudioNodeBase from "@/components/playbooks/studio/nodes/StudioNodeBase";
import type { StudioNodeData } from "@/lib/playbook-studio/canvas-types";

export default function AgentTaskNode(props: NodeProps) {
  return <StudioNodeBase {...props} type="agent_task" data={props.data as StudioNodeData} />;
}

"use client";

import type { NodeProps } from "@xyflow/react";
import StudioNodeBase from "@/components/playbooks/studio/nodes/StudioNodeBase";
import type { StudioNodeData } from "@/lib/playbook-studio/canvas-types";

export default function ArtifactNode(props: NodeProps) {
  return <StudioNodeBase {...props} type="artifact" data={props.data as StudioNodeData} />;
}

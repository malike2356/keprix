import type { PlaybookEvent } from "@/lib/playbook-api";

export type NodeRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "waiting_approval";

export function mapEventsToNodeStatus(
  events: PlaybookEvent[],
  nodeIds: string[],
): Record<string, NodeRunStatus> {
  const status: Record<string, NodeRunStatus> = Object.fromEntries(
    nodeIds.map((nodeId) => [nodeId, "pending" as NodeRunStatus]),
  );
  for (const event of events) {
    const node = event.payload.node;
    if (typeof node !== "string" || !(node in status)) continue;
    if (event.event_type === "playbook.node.started") status[node] = "running";
    if (event.event_type === "playbook.node.completed") status[node] = "completed";
    if (event.event_type === "playbook.node.failed") status[node] = "failed";
    if (event.event_type === "playbook.approval.requested") status[node] = "waiting_approval";
  }
  return status;
}

"use client";

import * as React from "react";
import { nodeKey } from "@/components/brain/graph-transform";
import { getApiBaseUrl } from "@/lib/ce-api";
import type { BrainActivationEvent } from "@/types/brain-graph";

export function useBrainActivation(sessionId: string | null) {
  const [activeNodeIds, setActiveNodeIds] = React.useState<Set<string>>(new Set());
  const [recentActivations, setRecentActivations] = React.useState<BrainActivationEvent[]>([]);
  const [paused, setPaused] = React.useState(false);

  React.useEffect(() => {
    if (!sessionId || paused) return;
    const es = new EventSource(`${getApiBaseUrl()}/api/brain/graph/activation-stream?session_id=${encodeURIComponent(sessionId)}`, { withCredentials: true });
    es.onmessage = (message) => {
      const event = JSON.parse(message.data) as BrainActivationEvent;
      const id = nodeKey(event.node_kind, event.node_id);
      setActiveNodeIds((prev) => new Set([...prev, id]));
      setRecentActivations((prev) => [event, ...prev].slice(0, 50));
      window.setTimeout(() => {
        setActiveNodeIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }, 3000);
    };
    return () => es.close();
  }, [paused, sessionId]);

  return {
    activeNodeIds,
    recentActivations,
    paused,
    setPaused,
    clearActivations: () => setRecentActivations([]),
  };
}

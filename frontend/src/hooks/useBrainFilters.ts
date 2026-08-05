"use client";

import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { BrainGraphFilters, BrainNodeKind } from "@/types/brain-graph";

export const ALL_KINDS: BrainNodeKind[] = ["memory", "skill", "task", "tool", "session", "document", "source", "entity"];

type Range = "all" | "today" | "7d" | "30d";

function sinceFor(range: Range): string | undefined {
  if (range === "all") return undefined;
  const date = new Date();
  if (range === "today") date.setHours(0, 0, 0, 0);
  if (range === "7d") date.setDate(date.getDate() - 7);
  if (range === "30d") date.setDate(date.getDate() - 30);
  return date.toISOString();
}

export function useBrainFilters(workspaceId = "default", options?: { syncUrl?: boolean }) {
  const syncUrl = options?.syncUrl !== false;
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const storageKey = `brain-graph-filters-${workspaceId}`;
  const initialKinds = params.get("kinds")?.split(",").filter(Boolean) as BrainNodeKind[] | undefined;
  const [kinds, setKinds] = React.useState<BrainNodeKind[]>(initialKinds?.length ? initialKinds : ALL_KINDS);
  const [range, setRange] = React.useState<Range>((params.get("since") as Range) || "all");
  const [sessionId, setSessionId] = React.useState(params.get("session_id") || "");
  const [query, setQuery] = React.useState(params.get("q") || "");

  React.useEffect(() => {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw || params.toString()) return;
    try {
      const saved = JSON.parse(raw) as { kinds?: BrainNodeKind[]; range?: Range };
      if (saved.kinds?.length) setKinds(saved.kinds);
      if (saved.range) setRange(saved.range);
    } catch {
      return;
    }
  }, [params, storageKey]);

  React.useEffect(() => {
    if (!syncUrl) return;
    window.localStorage.setItem(storageKey, JSON.stringify({ kinds, range }));
    const next = new URLSearchParams();
    if (kinds.length !== ALL_KINDS.length) next.set("kinds", kinds.join(","));
    if (range !== "all") next.set("since", range);
    if (sessionId) next.set("session_id", sessionId);
    if (query) next.set("q", query);
    const suffix = next.toString();
    router.replace(suffix ? `${pathname}?${suffix}` : pathname, { scroll: false });
  }, [kinds, pathname, query, range, router, sessionId, storageKey, syncUrl]);

  const filters: BrainGraphFilters = {
    kinds,
    sessionId: sessionId || undefined,
    since: sinceFor(range),
    limit: 500,
  };
  const clear = () => {
    setKinds(ALL_KINDS);
    setRange("all");
    setSessionId("");
    setQuery("");
  };
  return { filters, kinds, setKinds, range, setRange, sessionId, setSessionId, query, setQuery, clear };
}

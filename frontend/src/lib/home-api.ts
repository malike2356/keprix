import { ceApi } from "@/lib/ce-api";

export type HomeBrainStats = {
  memoryCount: number;
  skillCount: number;
  documentCount: number;
  sourceCount: number;
  toolCount: number;
};

type AdminStatsPayload = {
  tools_synthesised: number;
  active_tools?: number;
  memory_documents?: number;
};

function emptyHomeBrainStats(): HomeBrainStats {
  return {
    memoryCount: 0,
    skillCount: 0,
    documentCount: 0,
    sourceCount: 0,
    toolCount: 0,
  };
}

async function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  if (typeof AbortController === "undefined") return promise;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    // Callers that accept signal should use it; this races for fetch wrappers that do not.
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        controller.signal.addEventListener("abort", () => {
          reject(new Error("home stats timed out"));
        });
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchHomeBrainStats(): Promise<HomeBrainStats> {
  try {
    const graph = await withTimeout(ceApi("/api/brain/graph/stats"), 8_000);
    if (graph.ok) {
      const data = (await graph.json()) as { nodes_by_kind?: Record<string, number> };
      const counts = data.nodes_by_kind ?? {};
      return {
        memoryCount: counts.memory ?? 0,
        skillCount: counts.skill ?? 0,
        documentCount: counts.document ?? 0,
        sourceCount: counts.source ?? 0,
        toolCount: counts.tool ?? 0,
      };
    }
  } catch {
    /* fall through to older stats endpoints */
  }

  try {
    const res = await withTimeout(ceApi("/api/admin/stats"), 8_000);
    if (res.ok) {
      const data = (await res.json()) as AdminStatsPayload;
      return {
        memoryCount: data.memory_documents ?? 0,
        skillCount: 0,
        documentCount: 0,
        sourceCount: 0,
        toolCount: data.active_tools ?? data.tools_synthesised ?? 0,
      };
    }
  } catch {
    /* fall through to direct endpoints */
  }

  try {
    const [mem, tools] = await withTimeout(
      Promise.allSettled([
        ceApi("/api/stats/memory/count").then((r) => r.json() as Promise<{ count: number }>),
        ceApi("/api/stats/tools/count").then((r) => r.json() as Promise<{ count: number }>),
      ]),
      8_000,
    );
    return {
      memoryCount: mem.status === "fulfilled" ? (mem.value.count ?? 0) : 0,
      skillCount: 0,
      documentCount: 0,
      sourceCount: 0,
      toolCount: tools.status === "fulfilled" ? (tools.value.count ?? 0) : 0,
    };
  } catch {
    return emptyHomeBrainStats();
  }
}

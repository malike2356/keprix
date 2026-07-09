import { ceApi } from "@/lib/ce-api";

export type HomeBrainStats = {
  memoryCount: number;
  toolCount: number;
};

type AdminStatsPayload = {
  tools_synthesised: number;
  active_tools?: number;
  memory_documents?: number;
};

export async function fetchHomeBrainStats(): Promise<HomeBrainStats> {
  try {
    const res = await ceApi("/api/admin/stats");
    if (res.ok) {
      const data = (await res.json()) as AdminStatsPayload;
      return {
        memoryCount: data.memory_documents ?? 0,
        toolCount: data.active_tools ?? data.tools_synthesised ?? 0,
      };
    }
  } catch {
    /* fall through to direct endpoints */
  }

  const [mem, tools] = await Promise.allSettled([
    ceApi("/api/stats/memory/count").then((r) => r.json() as Promise<{ count: number }>),
    ceApi("/api/stats/tools/count").then((r) => r.json() as Promise<{ count: number }>),
  ]);
  return {
    memoryCount: mem.status === "fulfilled" ? (mem.value.count ?? 0) : 0,
    toolCount: tools.status === "fulfilled" ? (tools.value.count ?? 0) : 0,
  };
}

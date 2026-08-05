"use client";

import * as React from "react";
import { ceApi } from "@/lib/ce-api";

export type SkillRunStatus = "idle" | "running" | "done" | "error";

export type SkillRunResult = {
  skill: string;
  status: string;
  output: Record<string, unknown>;
  tokens_used: number;
  duration_ms: number;
  session_id: string;
  run_id: string;
  ledger_entry_id?: string | null;
  error?: string | null;
};

export function useSkillRunner(skillSlug: string) {
  const [status, setStatus] = React.useState<SkillRunStatus>("idle");
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<SkillRunResult | null>(null);

  const run = React.useCallback(async (params?: Record<string, unknown>) => {
    setStatus("running");
    setError(null);
    setResult(null);
    try {
      const response = await ceApi(`/api/skills/${encodeURIComponent(skillSlug)}/run`, {
        method: "POST",
        body: JSON.stringify({ params: params ?? {} }),
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as SkillRunResult;
      setResult(payload);
      setStatus("done");
      return payload;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Skill run failed";
      setError(message);
      setStatus("error");
      throw err;
    }
  }, [skillSlug]);

  return { run, status, error, result };
}

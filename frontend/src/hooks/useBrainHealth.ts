"use client";

import * as React from "react";
import useSWR from "swr";
import { fetchBrainHealth } from "@/lib/brain-health-api";
import type { BrainHealthReport } from "@/types/brain-health";

const REFRESH_MS = 5 * 60 * 1000;

export function useBrainHealth(options?: { enabled?: boolean }) {
  const enabled = options?.enabled !== false;
  const { data, error, isLoading, mutate } = useSWR<BrainHealthReport>(
    enabled ? "brain-health" : null,
    () => fetchBrainHealth(false),
    { refreshInterval: REFRESH_MS, revalidateOnFocus: true },
  );
  const [refreshError, setRefreshError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setRefreshError(null);
    try {
      const next = await fetchBrainHealth(true);
      await mutate(next, { revalidate: false });
      return next;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load brain health";
      setRefreshError(message);
      return null;
    }
  }, [mutate]);

  return {
    report: data ?? null,
    loading: isLoading,
    error:
      refreshError ||
      (error ? (error instanceof Error ? error.message : "Failed to load brain health") : null),
    refresh,
    mutate,
  };
}

"use client";

import useSWR from "swr";
import { fetchBuiltAppManifest } from "@/lib/built-apps-api";

export function useBuiltAppManifest(slug: string) {
  const { data, error, isLoading } = useSWR(slug ? ["built-app-manifest", slug] : null, () =>
    fetchBuiltAppManifest(slug),
  );

  return {
    manifest: data,
    error,
    isLoading,
  };
}

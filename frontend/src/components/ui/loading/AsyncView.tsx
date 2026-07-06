"use client";

import type { ReactNode } from "react";
import ErrorState from "@/components/ui/ErrorState";

type AsyncViewProps = {
  loading: boolean;
  error?: string | null;
  skeleton: ReactNode;
  children: ReactNode;
  errorTitle?: string;
};

export default function AsyncView({
  loading,
  error,
  skeleton,
  children,
  errorTitle = "Could not load content",
}: AsyncViewProps) {
  if (loading) {
    return <>{skeleton}</>;
  }
  if (error) {
    return <ErrorState title={errorTitle} message={error} />;
  }
  return <>{children}</>;
}

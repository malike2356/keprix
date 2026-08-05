"use client";

import Box from "@mui/material/Box";
import type { ReactNode } from "react";
import { SkeletonBlock } from "@/components/ui/loading";
import { useRequireSession } from "@/lib/ce-auth";

/**
 * Ensures the studio only renders once the workspace session has resolved,
 * so the canvas does not flash unauthenticated or redirect mid-render.
 */
export default function StudioHandoffGate({ children }: { children: ReactNode }) {
  const session = useRequireSession();

  if (session.isLoading || !session.user) {
    return (
      <Box sx={{ p: 2 }}>
        <SkeletonBlock height={480} />
      </Box>
    );
  }

  return <>{children}</>;
}

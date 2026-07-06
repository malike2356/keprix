"use client";

import ThemeRegistry from "@/components/providers/ThemeRegistry";

export function Providers({ children }: { children: React.ReactNode }) {
  return <ThemeRegistry>{children}</ThemeRegistry>;
}

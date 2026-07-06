"use client";

import { SessionProvider } from "@/lib/ce-auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}

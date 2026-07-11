"use client";

import { Suspense } from "react";
import { SessionProvider } from "@/lib/ce-auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <SessionProvider><Suspense>{children}</Suspense></SessionProvider>;
}

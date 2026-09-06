import type { Metadata } from "next";
import React from "react";

export const metadata: Metadata = {
  title: "Keprix Chat",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/favicon.ico", apple: "/apple-touch-icon.png" },
};

export default function ChatOnlyLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <>{children}</>;
}

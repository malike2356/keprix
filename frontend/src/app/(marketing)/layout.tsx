import type { Metadata } from "next";
import Box from "@mui/material/Box";
import { Navbar } from "@/components/marketing/Navbar";
import { Footer } from "@/components/marketing/Footer";

export const metadata: Metadata = {
  metadataBase: new URL("https://keprixai.uk"),
  title: {
    template: "%s | Keprix",
    default: "Keprix - The Mutant AI OS",
  },
  description:
    "Keprix is a self-hosted, MIT-licensed AI agent OS. Memory, tools, channels, playbooks, and a Mutation engine that builds new capabilities after your approval.",
  openGraph: {
    type: "website",
    siteName: "Keprix",
    locale: "en_GB",
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Navbar />
      <Box component="main" sx={{ flex: 1, width: "100%", overflowX: "hidden" }}>
        {children}
      </Box>
      <Footer />
    </Box>
  );
}

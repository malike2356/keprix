import type { Metadata } from "next";
import Box from "@mui/material/Box";
import { Navbar } from "@/components/marketing/Navbar";
import { Footer } from "@/components/marketing/Footer";

export const metadata: Metadata = {
  metadataBase: new URL("https://keprixai.com"),
  title: {
    template: "%s | Keprix",
    default: "Keprix - The self-mutating agent OS",
  },
  description:
    "Keprix is a self-hosted, self-mutating agent OS for people who need more than another AI chat box.",
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

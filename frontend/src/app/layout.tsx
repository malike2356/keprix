import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/app/providers";
import "./globals.css";
import "@/styles/voice-tailwind.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Keprix - The agent OS that writes its own tools",
  description: "Self-hosted open-source AI agent OS that can propose and test its own tools for your approval.",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16.png", sizes: "16x16", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} dark`} data-skin="default" suppressHydrationWarning>
      <head>
        <link rel="stylesheet" href="/themes/skins.css" />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var r=document.documentElement;var m=localStorage.getItem("keprix_theme_mode");var s=localStorage.getItem("keprix_theme_skin");if(m==="light"){r.classList.remove("dark");}else{r.classList.add("dark");}if(s){r.dataset.skin=s;}}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

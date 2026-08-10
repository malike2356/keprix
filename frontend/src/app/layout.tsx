import type { Metadata } from "next";
import { Inter, Inter_Tight } from "next/font/google";
import { Providers } from "@/app/providers";
import "./globals.css";
import "@/styles/voice-tailwind.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500"],
  variable: "--font-inter",
});

const interTight = Inter_Tight({
  subsets: ["latin"],
  display: "swap",
  weight: ["300", "500", "600"],
  variable: "--font-inter-tight",
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

/** Google AI Studio font stack (Flex / Text / Code); Inter fonts are local fallbacks. */
const AI_STUDIO_FONT_HREF =
  "https://fonts.googleapis.com/css2?"
  + "family=Google+Sans+Flex:opsz,wght@8..144,400..700"
  + "&family=Google+Sans+Text:ital,wght@0,400;0,500;0,600;1,400;1,500"
  + "&family=Google+Sans+Code:wght@400;500;600;700"
  + "&display=swap";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${interTight.variable} dark`}
      data-skin="default"
      suppressHydrationWarning
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href={AI_STUDIO_FONT_HREF} />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=VT323&display=swap" />
        <link rel="stylesheet" href="/themes/skins.css" />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var r=document.documentElement;var m=localStorage.getItem("keprix_theme_mode");var s=localStorage.getItem("keprix_theme_skin");if(m==="light"){r.classList.remove("dark");}else{r.classList.add("dark");}if(s){r.dataset.skin=s;}var cs=getComputedStyle(r);var dark=r.classList.contains("dark");var g=function(n,f){return (cs.getPropertyValue(n)||"").trim()||f;};r.style.setProperty("--kp-bg",g("--background",dark?"#0a0a0a":"#ffffff"));r.style.setProperty("--kp-bg-paper",g("--card",g("--background",dark?"#0a0a0a":"#ffffff")));r.style.setProperty("--kp-text-primary",g("--foreground",dark?"#fafafa":"#111827"));r.style.setProperty("--kp-text-secondary",g("--muted-foreground",dark?"#d1d5db":"#374151"));r.style.setProperty("--kp-border",g("--border",dark?"#262626":"rgba(0,0,0,0.12)"));r.style.setProperty("--kp-primary",g("--primary","#7c3aed"));r.style.setProperty("--kp-secondary",g("--secondary","#06b6d4"));}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { AppRouterCacheProvider } from "@mui/material-nextjs/v15-appRouter";
import { createKeprixTheme } from "@/theme/keprix-theme";
import { paletteFromCssVars } from "@/theme/palette-from-css";
import { pulseSkinChange, syncKeprixCssAliases } from "@/theme/sync-css-aliases";
import { rememberSkinId } from "@/theme/theme-recent";
import skinManifest from "@/theme/skin-manifest.json";
import type { KeprixPalette } from "@/theme/tokens/colors";
import { getKeprixColors, type ThemeMode } from "@/theme/tokens/colors";

const MODE_STORAGE_KEY = "keprix_theme_mode";
const SKIN_STORAGE_KEY = "keprix_theme_skin";
export const DEFAULT_THEME_SKIN = "default";

export type ThemeSkin = {
  id: string;
  label: string;
  primary: string;
  background: string;
  foreground: string;
};

export const THEME_SKINS: ThemeSkin[] = skinManifest.skins;

export function isMarketingPath(path: string): boolean {
  return (
    path === "/" ||
    path.startsWith("/docs") ||
    path.startsWith("/pricing") ||
    path.startsWith("/changelog") ||
    path.startsWith("/legal")
  );
}

function resolveWorkspaceMode(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem(MODE_STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return "dark";
}

function resolveWorkspaceSkin(): string {
  if (typeof window === "undefined") return DEFAULT_THEME_SKIN;
  const stored = localStorage.getItem(SKIN_STORAGE_KEY);
  if (stored && THEME_SKINS.some((skin) => skin.id === stored)) return stored;
  return DEFAULT_THEME_SKIN;
}

function applyDocumentTheme(mode: ThemeMode, skin: string) {
  const root = document.documentElement;
  root.dataset.skin = skin;
  root.classList.toggle("dark", mode === "dark");
  root.style.colorScheme = mode;
  window.requestAnimationFrame(() => {
    syncKeprixCssAliases();
  });
}

type ThemeContextValue = {
  mode: ThemeMode;
  skin: string;
  skins: ThemeSkin[];
  setMode: (mode: ThemeMode) => void;
  setSkin: (skin: string) => void;
  toggleMode: () => void;
};

const ThemeContext = React.createContext<ThemeContextValue | undefined>(undefined);

export function useThemeMode(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useThemeMode must be used within ThemeRegistry");
  }
  return ctx;
}

export default function ThemeRegistry({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mode, setModeState] = React.useState<ThemeMode>("dark");
  const [skin, setSkinState] = React.useState(DEFAULT_THEME_SKIN);
  const [palette, setPalette] = React.useState<KeprixPalette | null>(null);

  React.useEffect(() => {
    setModeState(resolveWorkspaceMode());
    setSkinState(resolveWorkspaceSkin());
  }, [pathname]);

  React.useEffect(() => {
    applyDocumentTheme(mode, skin);
    const frame = window.requestAnimationFrame(() => {
      setPalette(paletteFromCssVars(mode));
      syncKeprixCssAliases();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [mode, skin]);

  const setMode = React.useCallback((next: ThemeMode) => {
    setModeState(next);
    localStorage.setItem(MODE_STORAGE_KEY, next);
  }, []);

  const setSkin = React.useCallback((next: string) => {
    if (!THEME_SKINS.some((item) => item.id === next)) {
      return;
    }
    setSkinState(next);
    localStorage.setItem(SKIN_STORAGE_KEY, next);
    rememberSkinId(next);
    pulseSkinChange();
  }, []);

  const toggleMode = React.useCallback(() => {
    setMode(mode === "light" ? "dark" : "light");
  }, [mode, setMode]);

  const theme = React.useMemo(
    () => createKeprixTheme(mode, palette ?? getKeprixColors(mode)),
    [mode, palette],
  );

  const value = React.useMemo(
    () => ({ mode, skin, skins: THEME_SKINS, setMode, setSkin, toggleMode }),
    [mode, skin, setMode, setSkin, toggleMode],
  );

  return (
    <AppRouterCacheProvider options={{ key: "mui", prepend: true }}>
      <ThemeContext.Provider value={value}>
        <ThemeProvider theme={theme}>
          <CssBaseline enableColorScheme />
          {children}
        </ThemeProvider>
      </ThemeContext.Provider>
    </AppRouterCacheProvider>
  );
}

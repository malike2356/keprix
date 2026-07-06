"use client";

import * as React from "react";
import { THEME_SKINS, useThemeMode } from "@/components/providers/ThemeRegistry";

const MODE_KEY = "keprix_theme_mode";
const SKIN_KEY = "keprix_theme_skin";

export function WorkspaceThemeRestore() {
  const { setMode, setSkin } = useThemeMode();

  React.useEffect(() => {
    try {
      const m = localStorage.getItem(MODE_KEY);
      if (m === "light" || m === "dark") setMode(m);
      const s = localStorage.getItem(SKIN_KEY);
      if (s && THEME_SKINS.some((skin) => skin.id === s)) setSkin(s);
    } catch {
      // storage unavailable
    }
  }, [setMode, setSkin]);

  return null;
}
